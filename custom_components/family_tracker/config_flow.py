"""Configuration for Family Tracker."""

import probatio

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .apk_download import apk_download_placeholders
from .const import API_PATH, CREDENTIAL_FILE, DEFAULT_INTERVAL, DEFAULT_TIMEOUT, DOMAIN
from .fcm import Firebase
from .protocol import ProtocolError
from .server_url import public_server_url
from .services import NAME, whole_minutes

PAIRING_SCHEMA = probatio.Schema({
    probatio.Required("name"): selector.TextSelector(),
    probatio.Required("interval_minutes", default=DEFAULT_INTERVAL): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=1440, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
})


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
        server = public_server_url(self.hass.config)
        if server is None:
            return self.async_abort(reason="public_url_required")
        errors = {}
        if user_input is not None:
            project = user_input.get("project_id", "").strip()
            if project and not Firebase.valid_project(project):
                errors["project_id"] = "invalid_project"
            if project and not errors:
                firebase = Firebase(self.hass, project, self.hass.config.path(CREDENTIAL_FILE))
                try:
                    await firebase.validate()
                except Firebase.ConfigError:
                    errors["project_id"] = "invalid_credentials"
            if not errors:
                data = {**user_input, "project_id": project}
                if step == "reconfigure":
                    return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data_updates=data)
                return self.async_create_entry(title="Family Tracker", data=data)
        schema = probatio.Schema({
            probatio.Optional("project_id", default=defaults.get("project_id", "")): str,
            probatio.Required("timeout", default=defaults.get("timeout", DEFAULT_TIMEOUT)):
                probatio.All(probatio.Coerce(int), probatio.Range(min=15, max=300)),
        })
        return self.async_show_form(
            step_id=step,
            data_schema=schema,
            errors=errors,
            description_placeholders={
                **apk_download_placeholders(local=step == "reconfigure"), "server_url": server,
            },
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
        server = public_server_url(self.hass.config)
        if server is None:
            return self.async_abort(reason="public_url_required")
        errors = {}
        if user_input is not None:
            try:
                name = NAME(user_input["name"])
            except probatio.Invalid:
                errors["name"] = "invalid_name"
            try:
                interval = whole_minutes(user_input["interval_minutes"])
            except probatio.Invalid:
                errors["interval_minutes"] = "invalid_interval"
            if not errors:
                try:
                    paired = await manager.state.issue_pair(name, interval)
                except ProtocolError:
                    errors["base"] = "pairing_unavailable"
                else:
                    ticket = manager.pairing_downloads.issue(server, paired)
                    self._pairing_details = {
                        "qr_url": f"{API_PATH}/pairing_qr/{ticket}",
                        "code": paired["code"],
                    }
                    return await self.async_step_download()
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=PAIRING_SCHEMA,
            description_placeholders={**apk_download_placeholders(local=True), "server_url": server},
        )

    async def async_step_download(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="download", data_schema=probatio.Schema({}),
            description_placeholders=self._pairing_details,
        )
