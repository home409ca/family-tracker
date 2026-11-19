"""Device-only HTTPS API. HA administrator actions use the service registry."""

import asyncio
import json

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import API_PATH, DOMAIN
from .protocol import ProtocolError, fcm_token, fields, identifier, invalid, secret
from .pairing_qr import png

MAX_BODY = 8192
HEADERS = {"Cache-Control": "no-store"}


class DeviceView(HomeAssistantView):
    url = API_PATH + "/{operation}"
    name = "api:family_tracker:device"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request, operation):
        manager = self.hass.data.get(DOMAIN)
        if manager is None or not manager.ready:
            return web.json_response({"error": "unavailable"}, status=503, headers=HEADERS)
        try:
            result = await self._handle(manager, request, operation)
        except ProtocolError as err:
            headers = dict(HEADERS)
            if err.status == 429:
                headers["Retry-After"] = "60"
            return web.json_response({"error": err.code}, status=err.status, headers=headers)
        return web.json_response(result, headers=HEADERS)

    async def _handle(self, manager, request, operation):
        state = manager.state
        if operation not in ("pair", "report", "commands", "ack", "registration", "unpair"):
            raise ProtocolError(404, "unknown_operation")
        if request.content_type != "application/json":
            raise ProtocolError(415, "json_required")
        if request.content_length is not None and request.content_length > MAX_BODY:
            raise ProtocolError(413, "payload_too_large")
        if operation == "pair":
            state.limit(("pair", request.remote), 10, 60)
            state.limit(("pair",), 100, 60)
        else:
            try:
                device_id = identifier(request.headers.get("X-Family-Tracker-Device"))
                token = secret(request.headers.get("X-Family-Tracker-Token"))
                if operation == "unpair":
                    state.authenticate_unpair(device_id, token)
                else:
                    state.authenticate(device_id, token)
            except ProtocolError as err:
                state.limit(("unauthorized", request.remote), 30, 60)
                raise ProtocolError(401, "invalid_credentials") from err
            state.limit(("device", device_id), 90, 60)

        body = bytearray()
        async for chunk in request.content.iter_chunked(2048):
            body.extend(chunk)
            if len(body) > MAX_BODY:
                raise ProtocolError(413, "payload_too_large")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, RecursionError) as err:
            raise invalid() from err

        if operation == "pair":
            fields(payload, ("code",))
            result = await state.pair(secret(payload["code"]))
            manager.device_changed(result["device_id"], added=True)
            return result
        if operation == "report":
            result = await state.submit(device_id, token, payload)
            if not result["duplicate"]:
                manager.device_changed(device_id)
            return result
        if operation == "commands":
            fields(payload, ())
            return state.pending(device_id, token)
        if operation == "unpair":
            fields(payload, ())
            job = self.hass.async_create_task(
                manager.unpair(device_id, token), "Family Tracker unlink device",
            )
            await asyncio.shield(job)
            return {"removed": True}
        if operation == "ack":
            fields(payload, ("command_id", "stage"), ("error",))
            return await state.acknowledge(
                device_id, token, identifier(payload["command_id"]), payload["stage"], payload.get("error")
            )
        fields(payload, ("token",))
        await state.register_push(device_id, token, fcm_token(payload["token"]))
        return {"accepted": True}


class PairingQrView(HomeAssistantView):
    url = API_PATH + "/pairing_qr/{ticket}"
    name = "api:family_tracker:pairing_qr"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request, ticket):
        manager = self.hass.data.get(DOMAIN)
        headers = {**HEADERS, "Referrer-Policy": "no-referrer"}
        if manager is None or not manager.ready:
            return web.Response(status=404, headers=headers)
        try:
            payload = manager.pairing_downloads.take(ticket)
        except ProtocolError:
            return web.Response(status=404, headers=headers)
        image = await self.hass.async_add_executor_job(png, payload)
        headers["Content-Disposition"] = 'attachment; filename="family-tracker-parowanie.png"'
        return web.Response(body=image, content_type="image/png", headers=headers)
