"""Bridge between the persistent state and the HA entity platforms."""

from datetime import datetime
import logging

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import CREDENTIAL_FILE, DOMAIN
from .fcm import Firebase
from .pairing_qr import PairingDownloads
from .state import State

LOGGER = logging.getLogger(__name__)


class Manager:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.ready = False
        self.pairing_downloads = PairingDownloads()
        self.store = Store(hass, 1, DOMAIN, private=True, atomic_writes=True)
        project = entry.data.get("project_id")
        self.firebase = Firebase(hass, project, hass.config.path(CREDENTIAL_FILE)) if project else None

    async def load(self):
        self.state = State(await self.store.async_load(), self.store.async_save)

    @property
    def add_signal(self):
        return f"{DOMAIN}_{self.entry.entry_id}_add"

    def device_signal(self, device_id):
        return f"{DOMAIN}_{self.entry.entry_id}_{device_id}"

    @callback
    def device_changed(self, device_id, added=False):
        if added:
            async_dispatcher_send(self.hass, self.add_signal, device_id)
        async_dispatcher_send(self.hass, self.device_signal(device_id))

    @callback
    def rename_in_registry(self, device_id, name):
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier((DOMAIN, device_id), self.entry.entry_id)
        if device:
            registry.async_update_device(device.id, name=name)

    @callback
    def remove_from_registry(self, device_id):
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier((DOMAIN, device_id), self.entry.entry_id)
        if not device:
            return
        entities = er.async_get(self.hass)
        for entity in er.async_entries_for_device(entities, device.id, include_disabled_entities=True):
            if entity.platform == DOMAIN:
                entities.async_remove(entity.entity_id)
        registry.async_remove_device(device.id)

    async def send_command(self, device_id, kind, params):
        command, registration = await self.state.create_command(device_id, kind, params, self.entry.data["timeout"])
        if not self.firebase:
            result = "not_configured"
        elif not registration:
            result = "no_registration"
        else:
            expires = datetime.fromisoformat(command["expires_at"]).timestamp()
            result = await self.firebase.send(
                registration, command["id"], expires, urgent=kind == "request_location"
            )
        await self.state.push_result(device_id, command["id"], result, registration)
        if result not in ("sent", "not_configured", "no_registration"):
            LOGGER.warning("Family Tracker push status: %s", result)
        return self.state.command_status(device_id, command["id"])
