"""GPS position for the Home Assistant map."""

from homeassistant.components.device_tracker import TrackerEntity

from .entity import FamilyEntity, add_devices, utc


async def async_setup_entry(hass, entry, async_add_entities):
    add_devices(hass, entry, async_add_entities, (FamilyTracker,))


class FamilyTracker(FamilyEntity, TrackerEntity):
    _attr_name = None
    suffix = "location"
    keys = ("position",)

    @property
    def latitude(self):
        return self.current[0]["latitude"] if self.current[0] else None

    @property
    def longitude(self):
        return self.current[0]["longitude"] if self.current[0] else None

    @property
    def location_accuracy(self):
        return self.current[0]["accuracy"] if self.current[0] else 0

    @property
    def extra_state_attributes(self):
        fix = self.current[0]
        if fix:
            return {"last_seen": utc(fix["timestamp"]).isoformat(), "measurement_source": fix["source"]}
        return None
