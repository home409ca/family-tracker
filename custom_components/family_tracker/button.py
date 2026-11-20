"""Request a fresh location from a Family Tracker phone."""

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import FamilyEntity, add_devices


async def async_setup_entry(hass, entry, async_add_entities):
    add_devices(hass, entry, async_add_entities, (RequestLocation,))


class RequestLocation(FamilyEntity, ButtonEntity):
    _attr_translation_key = "request_location"
    _attr_icon = "mdi:crosshairs-gps"
    suffix = "refresh"

    async def async_press(self):
        await self.hass.services.async_call(
            DOMAIN, "request_location", {"device_id": self.device_id},
            blocking=True, context=self._context,
        )
