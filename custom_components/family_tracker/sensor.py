"""Battery and last contact sensors."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory

from .entity import FamilyEntity, add_devices, utc


async def async_setup_entry(hass, entry, async_add_entities):
    add_devices(hass, entry, async_add_entities, (Battery, LastContact, Wifi))


class Battery(FamilyEntity, SensorEntity):
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    suffix = "battery"

    def _values(self):
        battery = self.manager.state.data["devices"].get(self.device_id, {}).get("battery", {})
        return (battery.get("battery_level"),)

    @property
    def native_value(self):
        return self.current[0]


class LastContact(FamilyEntity, SensorEntity):
    _attr_name = "Last update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    suffix = "last_update"
    keys = ("published_contact",)

    @property
    def native_value(self):
        return utc(self.current[0]) if self.current[0] is not None else None


class Wifi(FamilyEntity, SensorEntity):
    _attr_name = "Wi-Fi"
    _attr_icon = "mdi:wifi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    suffix = "wifi"

    def _values(self):
        device = self.manager.state.data["devices"].get(self.device_id, {})
        return (device.get("wifi", {}).get("ssid"),)

    @property
    def native_value(self):
        return self.current[0]
