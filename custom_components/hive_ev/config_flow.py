"""Owner sign-in and SMS verification performed inside Home Assistant."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import probatio

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import HiveEVAuthError, HiveEVClient, HiveEVConnectionError, HiveEVError
from .auth import HiveEVLogin
from .const import DOMAIN, NAME, CONF_COST_RATE, CONF_COST_CURRENCY
from .cost_math import normalize_rate


class HiveEVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Do not retain the password or initiate MFA during background polling."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return HiveEVOptionsFlow()

    def __init__(self) -> None:
        self._login: HiveEVLogin | None = None
        self._tokens: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            if not username or username == "use@file.com" or not user_input[CONF_PASSWORD]:
                errors["base"] = "invalid_auth"
            else:
                self._login = HiveEVLogin(username, user_input[CONF_PASSWORD])
                try:
                    await self._login.async_start()
                    if self._login.requires_sms:
                        return await self.async_step_sms()
                    return await self._async_validate()
                except HiveEVAuthError:
                    errors["base"] = "invalid_auth"
                except HiveEVConnectionError:
                    errors["base"] = "cannot_connect"
                except HiveEVError:
                    errors["base"] = "invalid_response"
                finally:
                    if self._login is not None:
                        self._login.clear_password()
        return self.async_show_form(
            step_id="user", data_schema=probatio.Schema({
                probatio.Required(CONF_USERNAME): str,
                probatio.Required(CONF_PASSWORD): str,
            }), errors=errors,
        )

    async def async_step_sms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._login is None:
            return await self.async_step_user()
        errors = {}
        if user_input is not None:
            try:
                if self._login.requires_sms:
                    await self._login.async_sms(user_input["code"])
                return await self._async_validate()
            except HiveEVAuthError:
                errors["base"] = "invalid_code"
            except HiveEVConnectionError:
                errors["base"] = "cannot_connect"
            except HiveEVError:
                errors["base"] = "invalid_response"
        return self.async_show_form(
            step_id="sms", data_schema=probatio.Schema({probatio.Required("code"): str}), errors=errors,
        )

    async def _async_validate(self) -> ConfigFlowResult:
        assert self._login is not None
        self._tokens = self._login.tokens
        await self.async_set_unique_id(self._tokens["user_id"])
        if self.source == SOURCE_REAUTH:
            if self._get_reauth_entry().unique_id != self._tokens["user_id"]:
                return self.async_abort(reason="wrong_account")
        else:
            self._abort_if_unique_id_configured()
        # Confirm EV presence before offering account-side device registration.
        client = HiveEVClient(async_get_clientsession(self.hass), self._tokens)
        devices = await client.async_devices()
        if not devices:
            self._login.clear_password()
            self._login = None
            return self.async_abort(reason="no_chargers")
        if self._login.requires_registration:
            return await self.async_step_remember()
        return self._async_finish()

    async def async_step_remember(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A visible consent step before confirming a trusted sign-in device."""
        if self._login is None or self._tokens is None:
            return await self.async_step_user()
        errors = {}
        if user_input is not None:
            if user_input.get("remember_device") is not True:
                errors["base"] = "remember_required"
            else:
                try:
                    self._tokens = await self._login.async_register()
                    return self._async_finish()
                except HiveEVConnectionError:
                    errors["base"] = "cannot_connect"
                except HiveEVAuthError:
                    errors["base"] = "invalid_auth"
        return self.async_show_form(
            step_id="remember", data_schema=probatio.Schema({
                probatio.Required("remember_device", default=False): bool,
            }), errors=errors,
        )

    def _async_finish(self) -> ConfigFlowResult:
        assert self._tokens is not None
        if self._login is not None:
            self._login.clear_password()
        self._login = None
        data = {"tokens": self._tokens}
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data=data)
        return self.async_create_entry(title=NAME, data=data)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Always ask for a new interactive login; no stored account password."""
        return await self.async_step_user()


class HiveEVOptionsFlow(OptionsFlow):
    """Optional local cost estimate and explicit experimental enrollment."""

    async def async_step_init(self, user_input=None):
        errors = {}
        current = dict(getattr(self.config_entry, "options", {}))
        if user_input is not None:
            from .controls import controls_enabled
            options = {**current, **user_input}
            remove_cost = options.pop("remove_cost_helper", False)
            if remove_cost:
                options.pop(CONF_COST_RATE, None)
                options.pop(CONF_COST_CURRENCY, None)
            elif user_input.get(CONF_COST_RATE):
                selected = user_input[CONF_COST_RATE]
                state = self.hass.states.get(selected)
                rate = normalize_rate(state.state, state.attributes.get("unit_of_measurement")) if state else None
                # Retain an enrolled source/currency through temporary unavailability;
                # explicitly saving a now-valid new currency creates a separate total.
                if rate is not None:
                    options[CONF_COST_CURRENCY] = rate[0]
                elif selected != current.get(CONF_COST_RATE) or not current.get(CONF_COST_CURRENCY):
                    errors["base"] = "invalid_rate_sensor"
            if options.get("enable_experimental_controls") and not controls_enabled(options):
                errors["base"] = "alfen_confirmation_required"
            elif options.get("enable_experimental_controls") and len(getattr(getattr(self.config_entry, "runtime_data", None), "data", None) or {}) != 1:
                errors["base"] = "single_charger_required"
            if not errors:
                return self.async_create_entry(title="", data=options)
        schema = {
            probatio.Required("enable_experimental_controls", default=current.get("enable_experimental_controls", False)): bool,
            probatio.Required("owner_confirmed_alfen", default=current.get("owner_confirmed_alfen", False)): bool,
        }
        rate_key = (probatio.Optional(CONF_COST_RATE, default=current[CONF_COST_RATE])
                    if current.get(CONF_COST_RATE) else probatio.Optional(CONF_COST_RATE))
        schema[rate_key] = EntitySelector(EntitySelectorConfig(domain="sensor"))
        schema[probatio.Required("remove_cost_helper", default=False)] = bool
        return self.async_show_form(step_id="init", data_schema=probatio.Schema(schema), errors=errors)
