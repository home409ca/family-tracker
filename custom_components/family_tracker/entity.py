"""Shared HA entity behavior for a Family Tracker device."""

from datetime import datetime, timezone

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback

from .const import DOMAIN


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc)


@callback
def add_devices(hass, entry, async_add_entities, factories):
    manager = entry.runtime_data
    added = set()

    @callback
    def add(device_id):
        if device_id in added:
            return
        added.add(device_id)
        async_add_entities(factory(manager, device_id, added) for factory in factories)

    entry.async_on_unload(async_dispatcher_connect(hass, manager.add_signal, add))
    for device_id in manager.state.data["devices"]:
        add(device_id)


class FamilyEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    keys = ()

    def __init__(self, manager, device_id, added):
        self.manager = manager
        self.device_id = device_id
        self.added = added
        self._attr_unique_id = f"{device_id}_{self.suffix}"
        self.current = self._values()

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.manager.state.data["devices"].get(self.device_id, {}).get("name", "Family Tracker"),
            manufacturer="Family Tracker",
        )

    def _values(self):
        device = self.manager.state.data["devices"].get(self.device_id, {})
        return tuple(device.get(key) for key in self.keys)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, self.manager.device_signal(self.device_id), self._data_changed
        ))
        self._data_changed()

    async def async_will_remove_from_hass(self):
        self.added.discard(self.device_id)
        await super().async_will_remove_from_hass()

    @callback
    def _data_changed(self):
        values = self._values()
        if values != self.current:
            self.current = values
            self.async_write_ha_state()
