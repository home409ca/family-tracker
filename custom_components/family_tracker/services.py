"""HA administrator actions for pairing and remote commands."""

import json

import probatio

from homeassistant.core import SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.service import async_register_admin_service

from .const import DEFAULT_INTERVAL, DOMAIN
from .protocol import IDENTIFIER, ProtocolError
from .state import MAX_DEVICES

SERVICE_ID = probatio.All(str, probatio.Match(IDENTIFIER.pattern + "$"))


def whole_minutes(value):
    if type(value) not in (int, float) or not 1 <= value <= 1440 or value != int(value):
        raise probatio.Invalid("Enter a whole number of minutes from 1 to 1440")
    return int(value)


INTERVAL = whole_minutes
NAME = probatio.All(str, lambda value: value.strip(), probatio.Length(min=1, max=64))
DEVICE = {probatio.Required("device_id"): SERVICE_ID}
OPTIONAL_DEVICE = {probatio.Optional("device_id"): SERVICE_ID}
COMMANDS = {
    "request_location": DEVICE,
    "set_temporary_interval": {
        **DEVICE,
        probatio.Required("interval_minutes"): INTERVAL,
        probatio.Required("duration_minutes"): INTERVAL,
    },
    "set_interval": {**DEVICE, probatio.Required("interval_minutes"): INTERVAL},
    "reset_interval": DEVICE,
    "pause_reporting": DEVICE,
}


@callback
def register_services(hass):
    def register(name, fields, handler, response=SupportsResponse.ONLY):
        async def call(service):
            manager = hass.data.get(DOMAIN)
            if manager is None or not manager.ready:
                raise HomeAssistantError("Family Tracker is unavailable")
            try:
                return await handler(manager, dict(service.data))
            except ProtocolError as err:
                raise ServiceValidationError(err.code) from err

        async_register_admin_service(
            hass, DOMAIN, name, call,
            probatio.Schema(fields, extra=probatio.PREVENT_EXTRA),
            supports_response=response,
        )

    def register_command(name, fields):
        async def handle(manager, data):
            device_id = data.pop("device_id")
            return await manager.send_command(device_id, name, data)

        register(name, fields, handle, SupportsResponse.OPTIONAL)

    for name, fields in COMMANDS.items():
        register_command(name, fields)

    async def create_pairing(manager, data):
        device_id = data.get("device_id")
        if not device_id and "name" not in data:
            raise ServiceValidationError("Name is required for a new device")
        pair = await manager.state.issue_pair(
            data.get("name"), data["interval_minutes"], device_id
        )
        server = manager.entry.data["server_url"]
        return {
            **pair,
            "server_url": server,
            "qr_payload": json.dumps({"version": 1, "server_url": server, "code": pair["code"]}),
        }

    async def list_devices(manager, data):
        devices = manager.state.data["devices"]
        return {"devices": [
            {
                "device_id": key,
                "name": device["name"],
                "active": bool(device.get("token_hash")),
                "fcm_registered": bool(device.get("fcm_token")),
            }
            for key, device in list(devices.items())[:MAX_DEVICES]
        ]}

    async def command_status(manager, data):
        return manager.state.command_status(data["device_id"], data.get("command_id"))

    def register_management(name, operation, fields):
        async def handle(manager, data):
            device_id = data["device_id"]
            await manager.state.manage_device(device_id, operation, data.get("name"))
            if operation == "remove":
                manager.remove_from_registry(device_id)
            if operation == "rename":
                manager.rename_in_registry(device_id, data["name"])
            manager.device_changed(device_id)

        register(name, fields, handle, SupportsResponse.NONE)

    register("create_pairing", {
        **OPTIONAL_DEVICE,
        probatio.Optional("name"): NAME,
        probatio.Optional("interval_minutes", default=DEFAULT_INTERVAL): INTERVAL,
    }, create_pairing)
    register("list_devices", {}, list_devices)
    register("command_status", {**DEVICE, probatio.Optional("command_id"): SERVICE_ID}, command_status)
    register_management("rename_device", "rename", {**DEVICE, probatio.Required("name"): NAME})
    register_management("revoke_device", "revoke", DEVICE)
    register_management("remove_device", "remove", DEVICE)
