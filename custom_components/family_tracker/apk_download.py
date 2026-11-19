"""Public QR shown in the configuration dialog for installing the Android app."""

from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .const import API_PATH, DOMAIN

DOWNLOAD_URL = "https://github.com/home409ca/family-tracker/releases/latest"
QR_PATH = API_PATH + "/download/apk-qr.png"
QR_FILE = Path(__file__).with_name("brand") / "download-apk-qr.png"
REGISTERED = f"{DOMAIN}_apk_qr_view_registered"


class ApkQrView(HomeAssistantView):
    url = QR_PATH
    name = "api:family_tracker:apk_qr"
    requires_auth = False

    async def get(self, request):
        return web.FileResponse(QR_FILE, headers={"Cache-Control": "public, max-age=3600"})


@callback
def apk_download_placeholders(hass):
    """Register the image even when the first config entry is still being created."""
    if not hass.data.get(REGISTERED):
        hass.http.register_view(ApkQrView)
        hass.data[REGISTERED] = True
    return {"apk_download_url": DOWNLOAD_URL, "apk_qr_url": QR_PATH}
