"""Validation for the Family Tracker v1 API."""

from datetime import datetime, timezone
from math import isfinite
import re

IDENTIFIER = re.compile(r"[a-f0-9]{32}")
SECRET = re.compile(r"[A-Za-z0-9_-]{43}")
REPORT_MAX_AGE = 900
CLOCK_SKEW = 30
FAILURES = {
    "location_disabled", "permission_denied", "service_unavailable",
    "no_gps_fix", "consent_required", "superseded", "invalid_command",
}


class ProtocolError(Exception):
    def __init__(self, status, code):
        super().__init__(code)
        self.status = status
        self.code = code


def invalid():
    return ProtocolError(400, "invalid_payload")


def fields(data, required, optional=()):
    if not isinstance(data, dict):
        raise invalid()
    if not set(required) <= data.keys() or data.keys() - set(required) - set(optional):
        raise invalid()


def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise invalid()
    return value


def secret(value):
    if not isinstance(value, str) or not SECRET.fullmatch(value):
        raise invalid()
    return value


def timestamp(value, now):
    if not isinstance(value, str) or len(value) > 40:
        raise invalid()
    try:
        date = datetime.fromisoformat(value)
        if date.utcoffset() is None:
            raise ValueError
        seconds = date.timestamp()
    except (ValueError, OverflowError, OSError) as err:
        raise invalid() from err
    if not now - REPORT_MAX_AGE <= seconds <= now + CLOCK_SKEW:
        raise ProtocolError(422, "timestamp_out_of_range")
    return seconds


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def number(value, minimum, maximum):
    if type(value) not in (int, float) or not minimum <= value <= maximum or not isfinite(value):
        raise invalid()
    return float(value)


def fcm_token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_:\-]{16,4096}", value):
        raise invalid()
    return value


def report(data, now):
    fields(data, ("report_id", "app_version"), ("location", "battery", "wifi", "command_id"))
    identifier(data["report_id"])
    version = data["app_version"]
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9.+_-]{1,40}", version):
        raise invalid()
    if not data.keys() & {"location", "battery", "wifi"}:
        raise invalid()
    result = {"report_id": data["report_id"], "app_version": version}
    if "location" in data:
        location = data["location"]
        fields(location, ("latitude", "longitude", "accuracy", "source", "timestamp"))
        if location["source"] not in ("gps", "fused"):
            raise invalid()
        result["location"] = {
            "latitude": number(location["latitude"], -90, 90),
            "longitude": number(location["longitude"], -180, 180),
            "accuracy": number(location["accuracy"], 0, 100_000),
            "timestamp": timestamp(location["timestamp"], now),
            "source": location["source"],
        }
    if "battery" in data:
        battery = data["battery"]
        fields(battery, ("battery_level", "is_charging", "timestamp"))
        if type(battery["battery_level"]) is not int or not 0 <= battery["battery_level"] <= 100:
            raise invalid()
        if type(battery["is_charging"]) is not bool:
            raise invalid()
        result["battery"] = {
            **battery, "timestamp": timestamp(battery["timestamp"], now),
        }
    if "command_id" in data:
        result["command_id"] = identifier(data["command_id"])
        if result.get("location", {}).get("source") != "gps":
            raise ProtocolError(422, "fresh_gps_required")
    if "wifi" in data:
        wifi = data["wifi"]
        fields(wifi, ("ssid", "timestamp"))
        ssid = wifi["ssid"]
        if ssid is not None and (
            not isinstance(ssid, str) or not 1 <= len(ssid) <= 32
            or any(ord(char) < 32 or ord(char) == 127 for char in ssid)
        ):
            raise invalid()
        result["wifi"] = {"ssid": ssid, "timestamp": timestamp(wifi["timestamp"], now)}
    return result
