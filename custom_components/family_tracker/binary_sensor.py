"""Battery-charging state."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import FamilyEntity, add_devices


async def async_setup_entry(hass, entry, async_add_entities):
    add_devices(hass, entry, async_add_entities, (Charging,))


class Charging(FamilyEntity, BinarySensorEntity):
    _attr_name = "Charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    suffix = "charging"

    def _values(self):
        battery = self.manager.state.data["devices"].get(self.device_id, {}).get("battery", {})
        return (battery.get("is_charging"),)

    @property
    def is_on(self):
        return self.current[0]
