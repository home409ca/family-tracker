"""Public QR shown in the configuration dialog for installing the Android app."""

from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import API_PATH

DOWNLOAD_URL = "https://github.com/home409ca/family-tracker/releases/latest/download/FamilyTracker.apk"
QR_PATH = API_PATH + "/download/apk-qr.png"
QR_FILE = Path(__file__).with_name("brand") / "download-apk-qr.png"
HOSTED_QR = (
    "https://raw.githubusercontent.com/home409ca/family-tracker/HEAD/"
    "custom_components/family_tracker/brand/download-apk-qr.png"
)


class ApkQrView(HomeAssistantView):
    url = QR_PATH
    name = "api:family_tracker:apk_qr"
    requires_auth = False

    async def get(self, request):
        return web.FileResponse(QR_FILE, headers={"Cache-Control": "public, max-age=3600"})


def apk_download_placeholders(*, local):
    """Supply the public image independently of the setup lifecycle."""
    return {"apk_download_url": DOWNLOAD_URL, "apk_qr_url": QR_PATH if local else HOSTED_QR}
