"""Persistent device and command state, independent of Home Assistant."""

from asyncio import Lock
from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from math import asin, cos, radians, sin, sqrt
from secrets import token_urlsafe
from time import time
from uuid import uuid4

from .protocol import FAILURES, ProtocolError, invalid, iso, report

PAIR_TTL = 300
COMMAND_HISTORY = 86_400
MAX_COMMANDS = 128
MAX_DEVICES = 64
UNPAIR_RETRY_TTL = 86_400
TERMINAL = {"applied", "report_accepted", "failed", "report_accepted_late"}


def digest(value):
    return sha256(value.encode("ascii")).hexdigest()


def should_publish(old, new):
    if old is None:
        return True
    if new["timestamp"] <= old["timestamp"]:
        return False
    if all(old[key] == new[key] for key in ("latitude", "longitude", "accuracy", "source")):
        return False
    phi1, phi2 = radians(old["latitude"]), radians(new["latitude"])
    dlon = radians(new["longitude"] - old["longitude"])
    a = sin((phi2 - phi1) / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlon / 2) ** 2
    metres = 12_742_000 * asin(sqrt(min(1, a)))
    if new["timestamp"] - old["timestamp"] < 900:
        threshold = max(old["accuracy"], new["accuracy"])
    else:
        threshold = new["accuracy"] if new["accuracy"] >= old["accuracy"] else 0
    return new["accuracy"] < old["accuracy"] or metres > max(5, threshold)


class State:
    def __init__(self, initial, save, now=time):
        self.data = initial if initial is not None else {"devices": {}, "pairs": {}}
        for device in self.data["devices"].values():
            if "last_requested_fix" not in device:
                device["last_requested_fix"] = max(
                    (datetime.fromisoformat(receipt["received_at"]).timestamp()
                     for receipt in device.get("reports", {}).values()
                     if receipt.get("command_status") in ("report_accepted", "report_accepted_late")
                     and "received_at" in receipt),
                    default=None,
                )
        self._save = save
        self._now = now
        self._lock = Lock()
        self._limits = defaultdict(deque)

    async def change(self, action):
        async with self._lock:
            updated = deepcopy(self.data)
            result = action(updated, self._now())
            if updated != self.data:
                await self._save(updated)
                self.data = updated
            return result

    def limit(self, key, count, window):
        now = self._now()
        expired = [name for name, hits in self._limits.items() if hits[-1] <= now - 60]
        for name in expired:
            del self._limits[name]
        if key not in self._limits and len(self._limits) >= 2048:
            raise ProtocolError(429, "rate_limited")
        hits = self._limits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= count:
            raise ProtocolError(429, "rate_limited")
        hits.append(now)

    @staticmethod
    def _device(data, device_id):
        device = data["devices"].get(device_id)
        if device is None:
            raise ProtocolError(404, "unknown_device")
        return device

    @staticmethod
    def _authenticate(data, device_id, token):
        device = data["devices"].get(device_id)
        expected = device.get("token_hash") if device else None
        if not compare_digest(digest(token), expected or ("0" * 64)) or not expected:
            raise ProtocolError(401, "invalid_credentials")
        return device

    def authenticate(self, device_id, token):
        self._authenticate(self.data, device_id, token)

    def _authenticate_unpair(self, data, device_id, token, now):
        if device_id in data["devices"]:
            return self._authenticate(data, device_id, token)
        receipt = data.get("removed", {}).get(device_id)
        expected = receipt["token_hash"] if receipt and receipt["expires"] > now else None
        if not compare_digest(digest(token), expected or ("0" * 64)) or not expected:
            raise ProtocolError(401, "invalid_credentials")
        return None

    def authenticate_unpair(self, device_id, token):
        self._authenticate_unpair(self.data, device_id, token, self._now())

    @staticmethod
    def _remove_device(data, device_id, now):
        token_hash = data["devices"][device_id]["token_hash"]
        data["pairs"] = {
            key: pair for key, pair in data["pairs"].items() if pair["device_id"] != device_id
        }
        del data["devices"][device_id]
        if token_hash:
            receipts = {
                key: receipt for key, receipt in data.get("removed", {}).items() if receipt["expires"] > now
            }
            if len(receipts) >= MAX_DEVICES * 2:
                del receipts[next(iter(receipts))]
            receipts[device_id] = {"token_hash": token_hash, "expires": now + UNPAIR_RETRY_TTL}
            data["removed"] = receipts

    async def unpair(self, device_id, token):
        def apply(data, now):
            device = self._authenticate_unpair(data, device_id, token, now)
            if device is None:
                return
            self._remove_device(data, device_id, now)

        await self.change(apply)

    async def issue_pair(self, name, interval, device_id=None):
        code = token_urlsafe(32)

        def apply(data, now):
            pairs = data["pairs"]
            for key in list(pairs):
                if pairs[key]["expires"] <= now or (device_id and pairs[key]["device_id"] == device_id):
                    del pairs[key]
            if len(pairs) >= MAX_DEVICES:
                raise ProtocolError(429, "too_many_pairing_codes")
            if device_id:
                current = self._device(data, device_id)
                pair_name, pair_interval = current["name"], current["interval"]
            else:
                pair_name, pair_interval = name, interval
            pairs[digest(code)] = {
                "name": pair_name, "interval": pair_interval,
                "device_id": device_id, "expires": now + PAIR_TTL,
            }
            return {"code": code, "expires_at": iso(now + PAIR_TTL)}

        return await self.change(apply)

    async def pair(self, code):
        token = token_urlsafe(32)

        def apply(data, now):
            pair = data["pairs"].get(digest(code))
            if pair is None or pair["expires"] <= now:
                raise ProtocolError(401, "invalid_pairing_code")
            existing_id = pair["device_id"]
            if existing_id is None and len(data["devices"]) >= MAX_DEVICES:
                raise ProtocolError(409, "device_limit_reached")
            device_id = existing_id or uuid4().hex
            if existing_id:
                device = self._device(data, existing_id)
            else:
                device = {"name": pair["name"], "interval": pair["interval"]}
                data["devices"][device_id] = device
            device.update(token_hash=digest(token), fcm_token=None, commands={}, reports={})
            del data["pairs"][digest(code)]
            return {"device_id": device_id, "token": token, "interval_minutes": device["interval"]}

        return await self.change(apply)

    async def manage_device(self, device_id, operation, name=None):
        def apply(data, now):
            device = self._device(data, device_id)
            if operation == "rename":
                device["name"] = name
                return
            if operation == "remove":
                self._remove_device(data, device_id, now)
            else:
                data["pairs"] = {
                    key: pair for key, pair in data["pairs"].items() if pair["device_id"] != device_id
                }
                device.update(token_hash=None, fcm_token=None, commands={})

        await self.change(apply)

    async def register_push(self, device_id, token, registration):
        def apply(data, now):
            device = self._authenticate(data, device_id, token)
            if any(
                key != device_id and item.get("fcm_token") == registration
                for key, item in data["devices"].items()
            ):
                raise ProtocolError(409, "registration_already_used")
            device["fcm_token"] = registration

        await self.change(apply)

    async def confirm_push(self, device_id, token, command_id):
        def apply(data, now):
            device = self._authenticate(data, device_id, token)
            command = device["commands"].get(command_id)
            if command is None or command["push"] not in ("pending", "sent", "transport_error", "retryable_error"):
                return {"confirmed": False}
            if "push_confirmed_at" not in command:
                command["push_confirmed_at"] = now
                device["last_confirmed_push"] = now
            return {"confirmed": True}

        return await self.change(apply)

    async def create_command(self, device_id, kind, params, timeout):
        command_id = uuid4().hex

        def apply(data, now):
            device = self._device(data, device_id)
            if not device["token_hash"]:
                raise ProtocolError(409, "device_revoked")
            commands = device["commands"]
            if kind == "request_location" and any(
                value["kind"] == kind and value["expires"] > now and value["stage"] not in TERMINAL
                for value in commands.values()
            ):
                raise ProtocolError(409, "location_request_pending")
            for key in list(commands):
                if commands[key]["expires"] < now - COMMAND_HISTORY:
                    del commands[key]
            if len(commands) >= MAX_COMMANDS:
                oldest_finished = next(
                    (key for key, value in commands.items() if value["expires"] <= now), None
                )
                if oldest_finished is None:
                    raise ProtocolError(429, "too_many_pending_commands")
                del commands[oldest_finished]
            command = {
                "id": command_id, "kind": kind, "params": params, "issued": now,
                "expires": now + timeout, "stage": "queued", "push": "pending",
            }
            commands[command_id] = command
            return self.command_view(command, now), device.get("fcm_token")

        return await self.change(apply)

    async def push_result(self, device_id, command_id, result, registration):
        def apply(data, now):
            device = data["devices"].get(device_id)
            command = device and device["commands"].get(command_id)
            if not command:
                return
            command["push"] = result
            if result == "unregistered" and device["fcm_token"] == registration:
                device["fcm_token"] = None

        await self.change(apply)

    @staticmethod
    def command_view(command, now):
        stage = command["stage"]
        status = stage
        if now >= command["expires"] and stage not in TERMINAL:
            status = "timeout"
        elif stage == "queued" and command["push"] == "sent":
            status = "sent"
        return {
            "id": command["id"], "kind": command["kind"], "params": dict(command["params"]),
            "issued_at": iso(command["issued"]), "expires_at": iso(command["expires"]),
            "status": status, "last_stage": stage, "push": command["push"],
            **{key: command[key] for key in ("error",) if key in command},
        }

    def command_status(self, device_id, command_id=None):
        device = self._device(self.data, device_id)
        commands = device["commands"]
        if command_id is None:
            command_id = next(reversed(commands), None)
        if command_id not in commands:
            raise ProtocolError(404, "unknown_command")
        return self.command_view(commands[command_id], self._now())

    def latest_command(self, device):
        commands = device["commands"]
        return self.command_view(commands[next(reversed(commands))], self._now()) if commands else None

    def pending(self, device_id, token):
        device = self._authenticate(self.data, device_id, token)
        now = self._now()
        return {
            "wifi_reports": True,
            "server_time": iso(now),
            "commands": [
                self.command_view(command, now) for command in device["commands"].values()
                if command["expires"] > now and command["stage"] not in TERMINAL
            ],
        }

    @staticmethod
    def _command(device, command_id):
        if command_id not in device["commands"]:
            raise ProtocolError(404, "unknown_command")
        return device["commands"][command_id]

    async def acknowledge(self, device_id, token, command_id, stage, error):
        if stage not in ("received", "measured", "applied", "failed"):
            raise invalid()
        if stage == "failed":
            if not isinstance(error, str) or error not in FAILURES:
                raise invalid()
        elif error is not None:
            raise invalid()

        def apply(data, now):
            device = self._authenticate(data, device_id, token)
            command = self._command(device, command_id)
            old = command["stage"]
            if old in TERMINAL or old == stage or (old == "measured" and stage == "received"):
                return self.command_view(command, now)
            if now >= command["expires"] and stage != "measured":
                raise ProtocolError(409, "command_expired")
            if stage == "measured" and (command["kind"] != "request_location" or old != "received"):
                raise ProtocolError(409, "invalid_command_transition")
            if stage == "applied":
                if command["kind"] == "request_location" or old != "received":
                    raise ProtocolError(409, "invalid_command_transition")
                if command["kind"] == "set_interval":
                    sequence = device.get("interval_sequence", 0)
                    if command["issued"] >= sequence:
                        device["interval"] = command["params"]["interval_minutes"]
                        device["interval_sequence"] = command["issued"]
            command["stage"] = stage
            if error:
                command["error"] = error
            return self.command_view(command, now)

        return await self.change(apply)

    async def submit(self, device_id, token, payload):
        def apply(data, now):
            device = self._authenticate(data, device_id, token)
            if not isinstance(payload, dict):
                raise invalid()
            report_id = payload.get("report_id")
            if isinstance(report_id, str) and report_id in device["reports"]:
                return {**device["reports"][report_id], "duplicate": True}
            item = report(payload, now)
            position = item.get("location")
            command = None
            if command_id := item.get("command_id"):
                command = self._command(device, command_id)
                if command["kind"] != "request_location" or command["stage"] not in ("received", "measured"):
                    raise ProtocolError(409, "invalid_command_transition")
                if not command["issued"] <= position["timestamp"] <= command["expires"]:
                    raise ProtocolError(422, "fresh_gps_required")
            result = {"accepted": True, "duplicate": False, "position_updated": False}
            if position and position["timestamp"] > device.get("latest_fix_time", 0):
                device["latest_fix_time"] = position["timestamp"]
                if should_publish(device.get("position"), position):
                    device["position"] = position
                    result["position_updated"] = True
            battery = item.get("battery")
            if battery and battery["timestamp"] > device.get("battery", {}).get("timestamp", 0):
                device["battery"] = battery
            wifi = item.get("wifi")
            if wifi and wifi["timestamp"] > device.get("wifi", {}).get("timestamp", 0):
                device["wifi"] = wifi
            device.update(contact=now, app_version=item["app_version"])
            if now - device.get("published_contact", 0) >= 300:
                device["published_contact"] = now
            if command:
                command["stage"] = "report_accepted" if now < command["expires"] else "report_accepted_late"
                result["command_status"] = command["stage"]
                device["last_requested_fix"] = now
            device["reports"][item["report_id"]] = {**result, "received_at": iso(now)}
            if len(device["reports"]) > 128:
                del device["reports"][next(iter(device["reports"]))]
            return device["reports"][item["report_id"]]

        return await self.change(apply)
