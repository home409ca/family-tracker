"""Firebase HTTP v1 transport. Push carries the command ID only."""

import asyncio
import json
import re
from time import time

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from requests import Session
from requests.exceptions import RequestException

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class Firebase:
    def __init__(self, hass, project_id, credential_path):
        self._hass = hass
        self._project = project_id
        self._path = credential_path
        self._lock = asyncio.Lock()
        self._credentials = None

    class ConfigError(Exception):
        pass

    @staticmethod
    def valid_project(project_id):
        return isinstance(project_id, str) and bool(re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project_id))

    def _read_credentials(self):
        try:
            with open(self._path, encoding="utf-8") as stream:
                data = json.load(stream)
            if not isinstance(data, dict) or data.get("token_uri") != TOKEN_URI:
                raise ValueError
            if data.get("type") != "service_account":
                raise ValueError
            return service_account.Credentials.from_service_account_info(data, scopes=[SCOPE])
        except (OSError, ValueError, TypeError, GoogleAuthError) as err:
            raise self.ConfigError from err

    async def validate(self):
        async with self._lock:
            self._credentials = await self._hass.async_add_executor_job(self._read_credentials)

    def _send(self, registration, command_id, expires, urgent=False):
        try:
            if self._credentials is None:
                self._credentials = self._read_credentials()
            with Session() as session:
                if not self._credentials.valid:
                    def oauth_request(*args, **kwargs):
                        kwargs["timeout"] = 5
                        return Request(session=session)(*args, **kwargs)
                    self._credentials.refresh(oauth_request)
                remaining = int(expires - time())
                if remaining <= 0:
                    return "expired"
                response = session.post(
                    f"https://fcm.googleapis.com/v1/projects/{self._project}/messages:send",
                    headers={"Authorization": f"Bearer {self._credentials.token}"},
                    json={"message": {
                        "token": registration,
                        "data": {"command_id": command_id},
                        "android": {"priority": "HIGH" if urgent else "NORMAL", "ttl": f"{remaining}s"},
                    }},
                    timeout=5,
                    allow_redirects=False,
                )
                if response.ok and response.status_code == 200:
                    return "sent"
                try:
                    details = response.json().get("error", {}).get("details", [])
                except (ValueError, AttributeError):
                    details = []
                if isinstance(details, list) and any(
                    isinstance(item, dict) and item.get("errorCode") == "UNREGISTERED"
                    for item in details
                ):
                    return "unregistered"
                if response.status_code in (401, 403):
                    return "authorization_error"
                if response.status_code == 429 or response.status_code >= 500:
                    return "retryable_error"
                return "rejected"
        except self.ConfigError:
            return "credentials_unavailable"
        except (GoogleAuthError, RequestException):
            return "transport_error"

    async def send(self, registration, command_id, expires, urgent=False):
        async with self._lock:
            return await self._hass.async_add_executor_job(self._send, registration, command_id, expires, urgent)
