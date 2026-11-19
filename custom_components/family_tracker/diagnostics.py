"""Redacted config-entry diagnostics."""

from .protocol import iso


async def async_get_config_entry_diagnostics(hass, entry):
    manager = entry.runtime_data
    devices = manager.state.data["devices"]
    return {
        "firebase_configured": manager.firebase is not None,
        "timeout_seconds": entry.data["timeout"],
        "devices": [
            {
                "active": bool(device.get("token_hash")),
                "app_version": device.get("app_version"),
                "push_registered": bool(device.get("fcm_token")),
                "last_report_at": iso(device["contact"]) if "contact" in device else None,
                "last_command": _last_command(manager.state, device),
            }
            for device in devices.values()
        ],
    }


def _last_command(state, device):
    command = state.latest_command(device)
    if command is None:
        return None
    return {key: command[key] for key in ("kind", "status", "push", "issued_at")}
