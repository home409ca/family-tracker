"""Family Tracker custom integration."""

from .const import DOMAIN


async def async_setup(hass, config):
    from .apk_download import ApkQrView
    from .http import DeviceView, PairingQrView
    from .services import register_services

    hass.http.register_view(DeviceView(hass))
    hass.http.register_view(PairingQrView(hass))
    hass.http.register_view(ApkQrView())
    register_services(hass)
    return True


async def async_setup_entry(hass, entry):
    from homeassistant.const import Platform

    from .runtime import Manager

    manager = Manager(hass, entry)
    await manager.load()
    entry.runtime_data = manager
    hass.data[DOMAIN] = manager
    try:
        await hass.config_entries.async_forward_entry_setups(
            entry, (Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR)
        )
    except BaseException:
        hass.data.pop(DOMAIN, None)
        raise
    manager.ready = True
    return True


async def async_unload_entry(hass, entry):
    from homeassistant.const import Platform

    manager = entry.runtime_data
    manager.ready = False
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, (Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR)
    )
    if unloaded:
        hass.data.pop(DOMAIN, None)
    else:
        manager.ready = True
    return unloaded
