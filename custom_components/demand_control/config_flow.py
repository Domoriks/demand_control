"""Config flow for Demand Control — multi-step dynamic setup."""

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
    CONF_EV_CURRENT_SENSOR,
    CONF_EV_POWER_SENSOR,
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
    selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.POWER)
)

_CURRENT_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.CURRENT)
)

_NUMBER_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="number")
)

_ACTUATOR_MODE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value=ACTUATOR_MODE_CURRENT, label="EV Current (A)"),
            selector.SelectOptionDict(value=ACTUATOR_MODE_POWER, label="EV Power (kW)"),
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_entity(value: Any) -> str:
    """Strip and return string; empty string if falsy."""
    return str(value or "").strip()


def _normalize_mode(value: Any) -> str:
    """Return a supported actuator mode, defaulting to current."""
    mode = str(value or ACTUATOR_MODE_CURRENT).strip()
    return mode if mode in {ACTUATOR_MODE_CURRENT, ACTUATOR_MODE_POWER} else ACTUATOR_MODE_CURRENT


def _opt(key: str, data: dict) -> vol.Optional:
    """Optional field, pre-filled when an existing entity is present."""
    val = _normalize_entity(data.get(key, ""))
    return vol.Optional(key, default=val) if val else vol.Optional(key)


def _req(key: str, data: dict) -> vol.Required:
    """Required field, pre-filled when an existing entity is present."""
    val = _normalize_entity(data.get(key, ""))
    return vol.Required(key, default=val) if val else vol.Required(key)


# ---------------------------------------------------------------------------
# Step schemas
# ---------------------------------------------------------------------------


def _schema_sensors(data: dict) -> vol.Schema:
    """Step 1 — home + demand meter sensors."""
    return vol.Schema(
        {
            _req(CONF_HOME_POWER_SENSOR, data): _POWER_SENSOR_SELECTOR,
            _opt(CONF_CURRENT_AVERAGE_DEMAND_SENSOR, data): _POWER_SENSOR_SELECTOR,
            _opt(CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR, data): _POWER_SENSOR_SELECTOR,
        }
    )


def _schema_actuator_mode(data: dict) -> vol.Schema:
    """Step 2 — EV charger control mode."""
    return vol.Schema(
        {
            vol.Required(
                CONF_ACTUATOR_MODE,
                default=_normalize_mode(data.get(CONF_ACTUATOR_MODE, ACTUATOR_MODE_CURRENT)),
            ): _ACTUATOR_MODE_SELECTOR,
        }
    )


def _schema_actuator_entity(data: dict, mode: str) -> vol.Schema:
    """Step 3 — EV actuator entity + optional measurement sensors (mode-dependent)."""
    if mode == ACTUATOR_MODE_CURRENT:
        return vol.Schema(
            {
                _req(CONF_CURRENT_ACTUATOR_ENTITY, data): _NUMBER_ENTITY_SELECTOR,
                _opt(CONF_EV_CURRENT_SENSOR, data): _CURRENT_SENSOR_SELECTOR,
                _opt(CONF_EV_POWER_SENSOR, data): _POWER_SENSOR_SELECTOR,
            }
        )
    return vol.Schema(
        {
            _req(CONF_POWER_ACTUATOR_ENTITY, data): _NUMBER_ENTITY_SELECTOR,
            _opt(CONF_EV_POWER_SENSOR, data): _POWER_SENSOR_SELECTOR,
        }
    )


def _schema_limits(data: dict, mode: str) -> vol.Schema:
    """Step 4 — Charging limits (mode-dependent current/power fields)."""

    def _f(key: str, fallback: Any) -> Any:
        return data.get(key, fallback)

    schema: dict = {
        vol.Optional(CONF_SCAN_INTERVAL, default=_f(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=300)
        ),
        vol.Optional(CONF_MAX_HOME_DEMAND_KW, default=_f(CONF_MAX_HOME_DEMAND_KW, DEFAULT_MAX_HOME_DEMAND_KW)): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=100.0)
        ),
        vol.Optional(CONF_PHASE_COUNT, default=_f(CONF_PHASE_COUNT, DEFAULT_PHASE_COUNT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=3)
        ),
        vol.Optional(CONF_LINE_VOLTAGE_V, default=_f(CONF_LINE_VOLTAGE_V, DEFAULT_LINE_VOLTAGE_V)): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=500.0)
        ),
    }

    if mode == ACTUATOR_MODE_CURRENT:
        schema[
            vol.Optional(CONF_MIN_CHARGE_CURRENT_A, default=_f(CONF_MIN_CHARGE_CURRENT_A, DEFAULT_MIN_CHARGE_CURRENT_A))
        ] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0))
        schema[
            vol.Optional(CONF_MAX_CHARGE_CURRENT_A, default=_f(CONF_MAX_CHARGE_CURRENT_A, DEFAULT_MAX_CHARGE_CURRENT_A))
        ] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0))
        schema[
            vol.Optional(CONF_CURRENT_STEP_A, default=_f(CONF_CURRENT_STEP_A, DEFAULT_CURRENT_STEP_A))
        ] = vol.All(vol.Coerce(float), vol.Range(min=0.001, max=10.0))
    else:
        schema[
            vol.Optional(CONF_MAX_CHARGE_POWER_KW, default=_f(CONF_MAX_CHARGE_POWER_KW, DEFAULT_MAX_CHARGE_POWER_KW))
        ] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=200.0))
        schema[
            vol.Optional(CONF_POWER_STEP_KW, default=_f(CONF_POWER_STEP_KW, DEFAULT_POWER_STEP_KW))
        ] = vol.All(vol.Coerce(float), vol.Range(min=0.001, max=20.0))

    return vol.Schema(schema)


# ---------------------------------------------------------------------------
# Config flow  (4 steps)
# ---------------------------------------------------------------------------


class DemandControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a multi-step config flow for Demand Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow state."""
        self._data: dict[str, Any] = {}

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> DemandControlOptionsFlow:
        """Create options flow instance."""
        return DemandControlOptionsFlow(config_entry)

    # ------------------------------------------------------------------
    # Step 1 — Meter sensors
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 1: Select home meter sensors."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_actuator()

        return self.async_show_form(
            step_id="user",
            data_schema=_schema_sensors(self._data),
        )

    # ------------------------------------------------------------------
    # Step 2 — EV charger control mode
    # ------------------------------------------------------------------

    async def async_step_actuator(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 2: Select EV charger control mode."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_actuator_entity()

        return self.async_show_form(
            step_id="actuator",
            data_schema=_schema_actuator_mode(self._data),
        )

    # ------------------------------------------------------------------
    # Step 3 — EV charger entity & measurement sensors (mode-dependent)
    # ------------------------------------------------------------------

    async def async_step_actuator_entity(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 3: EV charger entity and optional real-time measurement sensors."""
        errors: dict[str, str] = {}
        mode = _normalize_mode(self._data.get(CONF_ACTUATOR_MODE))

        if user_input is not None:
            entity_key = CONF_CURRENT_ACTUATOR_ENTITY if mode == ACTUATOR_MODE_CURRENT else CONF_POWER_ACTUATOR_ENTITY
            if not _normalize_entity(user_input.get(entity_key)):
                errors["base"] = (
                    "missing_current_actuator" if mode == ACTUATOR_MODE_CURRENT else "missing_power_actuator"
                )
            else:
                self._data.update(user_input)
                return await self.async_step_limits()

        return self.async_show_form(
            step_id="actuator_entity",
            data_schema=_schema_actuator_entity(self._data, mode),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 4 — Charging limits (mode-dependent)
    # ------------------------------------------------------------------

    async def async_step_limits(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 4: Charging limits and control parameters."""
        mode = _normalize_mode(self._data.get(CONF_ACTUATOR_MODE))

        if user_input is not None:
            self._data.update(user_input)

            actuator_key = CONF_CURRENT_ACTUATOR_ENTITY if mode == ACTUATOR_MODE_CURRENT else CONF_POWER_ACTUATOR_ENTITY
            unique_seed = _normalize_entity(self._data.get(actuator_key)) or _normalize_entity(
                self._data.get(CONF_HOME_POWER_SENSOR)
            )
            if unique_seed:
                await self.async_set_unique_id(unique_seed.lower())
                self._abort_if_unique_id_configured()

            return self.async_create_entry(title="Demand Control", data=self._data)

        return self.async_show_form(
            step_id="limits",
            data_schema=_schema_limits(self._data, mode),
        )


# ---------------------------------------------------------------------------
# Options flow  (same 4 steps, pre-populated from existing entry)
# ---------------------------------------------------------------------------


class DemandControlOptionsFlow(config_entries.OptionsFlow):
    """Handle Demand Control options — identical step sequence to config flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize with merged data + options so all fields are pre-populated."""
        self._config_entry = config_entry
        # Options take precedence over data; all keys are available across steps.
        self._options: dict[str, Any] = {**config_entry.data, **config_entry.options}

    # ------------------------------------------------------------------
    # Step 1 — Meter sensors
    # ------------------------------------------------------------------

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 1: Update home meter sensors."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_actuator()

        return self.async_show_form(
            step_id="init",
            data_schema=_schema_sensors(self._options),
        )

    # ------------------------------------------------------------------
    # Step 2 — EV charger control mode
    # ------------------------------------------------------------------

    async def async_step_actuator(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 2: Update EV charger control mode."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_actuator_entity()

        return self.async_show_form(
            step_id="actuator",
            data_schema=_schema_actuator_mode(self._options),
        )

    # ------------------------------------------------------------------
    # Step 3 — EV charger entity & measurement sensors (mode-dependent)
    # ------------------------------------------------------------------

    async def async_step_actuator_entity(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 3: Update EV charger entity and optional measurement sensors."""
        errors: dict[str, str] = {}
        mode = _normalize_mode(self._options.get(CONF_ACTUATOR_MODE))

        if user_input is not None:
            entity_key = CONF_CURRENT_ACTUATOR_ENTITY if mode == ACTUATOR_MODE_CURRENT else CONF_POWER_ACTUATOR_ENTITY
            if not _normalize_entity(user_input.get(entity_key)):
                errors["base"] = (
                    "missing_current_actuator" if mode == ACTUATOR_MODE_CURRENT else "missing_power_actuator"
                )
            else:
                self._options.update(user_input)
                return await self.async_step_limits()

        return self.async_show_form(
            step_id="actuator_entity",
            data_schema=_schema_actuator_entity(self._options, mode),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 4 — Charging limits (mode-dependent)
    # ------------------------------------------------------------------

    async def async_step_limits(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 4: Update charging limits and control parameters."""
        mode = _normalize_mode(self._options.get(CONF_ACTUATOR_MODE))

        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="limits",
            data_schema=_schema_limits(self._options, mode),
        )
