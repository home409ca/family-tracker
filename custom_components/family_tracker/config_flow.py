"""Configuration for Family Tracker."""

from urllib.parse import urlsplit

import probatio

from homeassistant import config_entries
from homeassistant.core import callback

from .apk_download import apk_download_placeholders
from .const import API_PATH, CREDENTIAL_FILE, DEFAULT_INTERVAL, DEFAULT_TIMEOUT, DOMAIN
from .fcm import Firebase
from .protocol import ProtocolError
from .services import INTERVAL, NAME

DEFAULT_SERVER = ""


def validate_url(value):
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        _ = parts.port
    except ValueError:
        return False
    return bool(
        parts.scheme == "https" and hostname and parts.path in ("", "/")
        and not parts.username and not parts.password and not parts.query and not parts.fragment
        and not any(ch.isspace() or ch in "\\\\" for ch in value)
    )


class FamilyTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PairingOptions()

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return await self._form("user", user_input, {})

    async def async_step_reconfigure(self, user_input=None):
        return await self._form("reconfigure", user_input, self._get_reconfigure_entry().data)

    async def _form(self, step, user_input, defaults):
        errors = {}
        if user_input is not None:
            server = user_input["server_url"].strip().rstrip("/")
            project = user_input.get("project_id", "").strip()
            if not validate_url(server):
                errors["server_url"] = "invalid_url"
            if project and not Firebase.valid_project(project):
                errors["project_id"] = "invalid_project"
            if project and not errors:
                firebase = Firebase(self.hass, project, self.hass.config.path(CREDENTIAL_FILE))
                try:
                    await firebase.validate()
                except Firebase.ConfigError:
                    errors["project_id"] = "invalid_credentials"
            if not errors:
                data = {**user_input, "server_url": server, "project_id": project}
                if step == "reconfigure":
                    return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data_updates=data)
                return self.async_create_entry(title="Family Tracker", data=data)
        schema = probatio.Schema({
            probatio.Required("server_url", default=defaults.get("server_url", DEFAULT_SERVER)): str,
            probatio.Optional("project_id", default=defaults.get("project_id", "")): str,
            probatio.Required("timeout", default=defaults.get("timeout", DEFAULT_TIMEOUT)):
                probatio.All(probatio.Coerce(int), probatio.Range(min=15, max=300)),
        })
        return self.async_show_form(
            step_id=step,
            data_schema=schema,
            errors=errors,
            description_placeholders=apk_download_placeholders(local=step == "reconfigure"),
        )


class PairingOptions(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        manager = self.hass.data.get(DOMAIN)
        if manager is None or not manager.ready:
            return self.async_abort(reason="unavailable")
        if user_id := self.context.get("user_id"):
            user = await self.hass.auth.async_get_user(user_id)
            if user is None or not user.is_admin:
                return self.async_abort(reason="unauthorized")
        errors = {}
        if user_input is not None:
            try:
                paired = await manager.state.issue_pair(user_input["name"], user_input["interval_minutes"])
            except ProtocolError:
                errors["base"] = "pairing_unavailable"
            else:
                server = self.config_entry.data["server_url"]
                ticket = manager.pairing_downloads.issue(server, paired)
                self._pairing_details = {
                    "qr_url": f"{server}{API_PATH}/pairing_qr/{ticket}",
                    "code": paired["code"],
                }
                return await self.async_step_download()
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=probatio.Schema({
                probatio.Required("name"): NAME,
                probatio.Required("interval_minutes", default=DEFAULT_INTERVAL): INTERVAL,
            }),
            description_placeholders=apk_download_placeholders(local=True),
        )

    async def async_step_download(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="download", data_schema=probatio.Schema({}),
            description_placeholders=self._pairing_details,
        )
