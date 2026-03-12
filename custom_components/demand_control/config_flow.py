"""Config flow for Demand Control."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ACTUATOR_MODE_CURRENT,
    ACTUATOR_MODE_POWER,
    CONF_ACTUATOR_MODE,
    CONF_CURRENT_ACTUATOR_ENTITY,
    CONF_CURRENT_AVERAGE_DEMAND_SENSOR,
    CONF_CURRENT_STEP_A,
    CONF_HOME_POWER_SENSOR,
    CONF_LINE_VOLTAGE_V,
    CONF_MAX_CHARGE_CURRENT_A,
    CONF_MAX_CHARGE_POWER_KW,
    CONF_MAX_HOME_DEMAND_KW,
    CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR,
    CONF_MIN_CHARGE_CURRENT_A,
    CONF_PHASE_COUNT,
    CONF_POWER_ACTUATOR_ENTITY,
    CONF_POWER_STEP_KW,
    CONF_SCAN_INTERVAL,
    DEFAULT_CURRENT_STEP_A,
    DEFAULT_LINE_VOLTAGE_V,
    DEFAULT_MAX_CHARGE_CURRENT_A,
    DEFAULT_MAX_CHARGE_POWER_KW,
    DEFAULT_MAX_HOME_DEMAND_KW,
    DEFAULT_MIN_CHARGE_CURRENT_A,
    DEFAULT_PHASE_COUNT,
    DEFAULT_POWER_STEP_KW,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_POWER_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="sensor",
        device_class=SensorDeviceClass.POWER,
    )
)

_NUMBER_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="number")
)

_ACTUATOR_MODE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value=ACTUATOR_MODE_CURRENT, label="Current (A)"),
            selector.SelectOptionDict(value=ACTUATOR_MODE_POWER, label="Power (kW)"),
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


def _build_schema(options: dict[str, Any], data: dict[str, Any]) -> vol.Schema:
    """Build schema with options values falling back to entry data."""

    def _default_value(key: str, fallback: Any) -> Any:
        value = options.get(key, data.get(key, fallback))
        return value

    return vol.Schema(
        {
            vol.Required(
                CONF_HOME_POWER_SENSOR,
                default=_default_value(CONF_HOME_POWER_SENSOR, ""),
            ): _POWER_SENSOR_SELECTOR,
            vol.Optional(
                CONF_CURRENT_AVERAGE_DEMAND_SENSOR,
                default=_default_value(CONF_CURRENT_AVERAGE_DEMAND_SENSOR, ""),
            ): _POWER_SENSOR_SELECTOR,
            vol.Optional(
                CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR,
                default=_default_value(CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR, ""),
            ): _POWER_SENSOR_SELECTOR,
            vol.Required(
                CONF_ACTUATOR_MODE,
                default=_default_value(CONF_ACTUATOR_MODE, ACTUATOR_MODE_CURRENT),
            ): _ACTUATOR_MODE_SELECTOR,
            vol.Optional(
                CONF_CURRENT_ACTUATOR_ENTITY,
                default=_default_value(CONF_CURRENT_ACTUATOR_ENTITY, ""),
            ): _NUMBER_ENTITY_SELECTOR,
            vol.Optional(
                CONF_POWER_ACTUATOR_ENTITY,
                default=_default_value(CONF_POWER_ACTUATOR_ENTITY, ""),
            ): _NUMBER_ENTITY_SELECTOR,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=_default_value(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Optional(
                CONF_MAX_HOME_DEMAND_KW,
                default=_default_value(CONF_MAX_HOME_DEMAND_KW, DEFAULT_MAX_HOME_DEMAND_KW),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Optional(
                CONF_PHASE_COUNT,
                default=_default_value(CONF_PHASE_COUNT, DEFAULT_PHASE_COUNT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
            vol.Optional(
                CONF_LINE_VOLTAGE_V,
                default=_default_value(CONF_LINE_VOLTAGE_V, DEFAULT_LINE_VOLTAGE_V),
            ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=500.0)),
            vol.Optional(
                CONF_MIN_CHARGE_CURRENT_A,
                default=_default_value(CONF_MIN_CHARGE_CURRENT_A, DEFAULT_MIN_CHARGE_CURRENT_A),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Optional(
                CONF_MAX_CHARGE_CURRENT_A,
                default=_default_value(CONF_MAX_CHARGE_CURRENT_A, DEFAULT_MAX_CHARGE_CURRENT_A),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Optional(
                CONF_MAX_CHARGE_POWER_KW,
                default=_default_value(CONF_MAX_CHARGE_POWER_KW, DEFAULT_MAX_CHARGE_POWER_KW),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=200.0)),
            vol.Optional(
                CONF_CURRENT_STEP_A,
                default=_default_value(CONF_CURRENT_STEP_A, DEFAULT_CURRENT_STEP_A),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.001, max=10.0)),
            vol.Optional(
                CONF_POWER_STEP_KW,
                default=_default_value(CONF_POWER_STEP_KW, DEFAULT_POWER_STEP_KW),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.001, max=20.0)),
        }
    )


def _normalize_optional_entity(value: Any) -> str:
    """Normalize optional entity selector values to a stripped string."""
    return str(value or "").strip()


def _validate_mode_requirements(user_input: dict[str, Any]) -> str | None:
    """Validate actuator mode dependent requirements."""
    mode = str(user_input.get(CONF_ACTUATOR_MODE, ACTUATOR_MODE_CURRENT)).strip()
    current_entity = _normalize_optional_entity(user_input.get(CONF_CURRENT_ACTUATOR_ENTITY))
    power_entity = _normalize_optional_entity(user_input.get(CONF_POWER_ACTUATOR_ENTITY))

    if mode == ACTUATOR_MODE_CURRENT and not current_entity:
        return "missing_current_actuator"
    if mode == ACTUATOR_MODE_POWER and not power_entity:
        return "missing_power_actuator"

    return None


class DemandControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Demand Control."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> DemandControlOptionsFlow:
        """Create options flow instance."""
        return DemandControlOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error_key = _validate_mode_requirements(user_input)
            if error_key is None:
                mode = str(user_input.get(CONF_ACTUATOR_MODE, ACTUATOR_MODE_CURRENT)).strip()
                actuator_entity = _normalize_optional_entity(
                    user_input.get(
                        CONF_CURRENT_ACTUATOR_ENTITY if mode == ACTUATOR_MODE_CURRENT else CONF_POWER_ACTUATOR_ENTITY
                    )
                )
                unique_seed = actuator_entity or _normalize_optional_entity(user_input.get(CONF_HOME_POWER_SENSOR))
                if unique_seed:
                    await self.async_set_unique_id(unique_seed.lower())
                    self._abort_if_unique_id_configured()

                return self.async_create_entry(title="Demand Control", data=user_input)

            errors["base"] = error_key

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}, {}),
            errors=errors,
        )


class DemandControlOptionsFlow(config_entries.OptionsFlow):
    """Handle Demand Control options updates."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error_key = _validate_mode_requirements(user_input)
            if error_key is None:
                merged = {**self._config_entry.options, **user_input}
                return self.async_create_entry(title="", data=merged)

            errors["base"] = error_key

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(self._config_entry.options, self._config_entry.data),
            errors=errors,
        )
