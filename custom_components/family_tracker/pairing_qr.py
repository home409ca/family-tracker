"""Produce private, short-lived downloads for the pairing form."""

from datetime import datetime
from io import BytesIO
import json
from secrets import token_urlsafe
from time import time

import qrcode

from .protocol import ProtocolError, secret


class PairingDownloads:
    def __init__(self):
        self._downloads = {}

    def issue(self, origin, pairing):
        now = time()
        self._downloads = {
            key: item for key, item in self._downloads.items() if item[0] > now
        }
        ticket = token_urlsafe(32)
        expires = datetime.fromisoformat(pairing["expires_at"]).timestamp()
        self._downloads[ticket] = (expires, origin, pairing["code"])
        return ticket

    def take(self, ticket):
        try:
            secret(ticket)
            expires, origin, code = self._downloads.pop(ticket)
        except (KeyError, ProtocolError) as err:
            raise ProtocolError(404, "qr_missing") from err
        if expires <= time():
            raise ProtocolError(404, "qr_missing")
        return json.dumps({"version": 1, "server_url": origin, "code": code}, separators=(",", ":"))


def png(payload):
    output = BytesIO()
    qrcode.make(payload, box_size=9, border=4).save(output, format="PNG")
    return output.getvalue()
