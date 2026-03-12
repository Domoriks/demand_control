"""Coordinator for Demand Control updates and EV actuator writes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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

_LOGGER = logging.getLogger(__name__)


class DemandControlUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage dynamic demand control state and EV actuator writes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the demand control coordinator."""
        self.entry = entry
        self._last_demand_kw: float | None = None
        self._demand_interval_start: datetime | None = None
        self._resume_lockout_until: datetime | None = None
        self._last_logged_status: str | None = None
        self._last_logged_target: float | None = None

        scan_interval = max(self._entry_int(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL), 1)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    def _entry_raw(self, key: str, default: Any) -> Any:
        """Read value from options first and then entry data."""
        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _entry_text(self, key: str, default: str = "") -> str:
        """Read and normalize a string setting."""
        raw = self._entry_raw(key, default)
        return str(raw).strip() if raw is not None else default

    def _entry_float(self, key: str, default: float) -> float:
        """Read and parse a float setting."""
        raw = self._entry_raw(key, default)
        parsed = self._as_float(raw)
        return parsed if parsed is not None else default

    def _entry_int(self, key: str, default: int) -> int:
        """Read and parse an int setting."""
        raw = self._entry_raw(key, default)
        parsed = self._as_float(raw)
        if parsed is None:
            return default
        return int(round(parsed))

    @staticmethod
    def _as_float(value: Any) -> float | None:
        """Best-effort conversion to float."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _round_to_step(value: float, step: float) -> float:
        """Round a value to the nearest supported step."""
        if step <= 0:
            return value
        return round(round(value / step) * step, 3)

    def _state_float(self, entity_id: str) -> float | None:
        """Read a numeric state from an entity."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return self._as_float(state.state)

    def _sensor_state_to_kw(self, entity_id: str) -> float | None:
        """Read a sensor state and normalize power to kW."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None

        value = self._as_float(state.state)
        if value is None:
            return None

        unit = str(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "")).strip().lower()
        if unit in {"w", "watt", "watts"}:
            return value / 1000
        if unit in {"kw", "kilowatt", "kilowatts"}:
            return value
        if unit in {"mw", "megawatt", "megawatts"}:
            return value * 1000

        # Fallback heuristic for sensors that report numeric values without units.
        return value / 1000 if value > 200 else value

    def _update_demand_interval_on_falling_edge(self, now: datetime, demand_kw: float) -> None:
        """Track 15-minute demand interval by detecting a falling edge."""
        if self._demand_interval_start is None:
            self._demand_interval_start = now
        elif self._last_demand_kw is not None and demand_kw < (self._last_demand_kw - 0.05):
            self._demand_interval_start = now

        self._last_demand_kw = demand_kw

    @staticmethod
    def _lockout_remaining_text(lockout_remaining: timedelta | None) -> str | None:
        """Format a lockout duration for concise logs."""
        if lockout_remaining is None:
            return None

        total_seconds = max(int(lockout_remaining.total_seconds()), 0)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _log_control_state(
        self,
        *,
        status: str,
        target: float | None,
        mode: str,
        home_power_kw: float | None,
        current_average_demand_kw: float | None,
        projected_peak_kw: float | None,
        lockout_active: bool,
        lockout_remaining: timedelta | None,
    ) -> None:
        """Emit state-change logs without spamming every coordinator tick."""
        if status == self._last_logged_status and target == self._last_logged_target:
            return

        _LOGGER.debug(
            "Demand control status=%s mode=%s target=%s home_power_kw=%s current_average_demand_kw=%s "
            "projected_peak_kw=%s lockout=%s lockout_remaining=%s",
            status,
            mode,
            target,
            f"{home_power_kw:.3f}" if home_power_kw is not None else None,
            f"{current_average_demand_kw:.3f}" if current_average_demand_kw is not None else None,
            f"{projected_peak_kw:.3f}" if projected_peak_kw is not None else None,
            lockout_active,
            self._lockout_remaining_text(lockout_remaining),
        )

        self._last_logged_status = status
        self._last_logged_target = target

    async def _async_update_data(self) -> dict[str, Any]:
        """Compute demand-control targets and optionally write EV actuator values."""
        mode = self._entry_text(CONF_ACTUATOR_MODE, ACTUATOR_MODE_CURRENT)
        if mode not in {ACTUATOR_MODE_CURRENT, ACTUATOR_MODE_POWER}:
            mode = ACTUATOR_MODE_CURRENT

        ev_actuator_entity = self._entry_text(
            CONF_CURRENT_ACTUATOR_ENTITY if mode == ACTUATOR_MODE_CURRENT else CONF_POWER_ACTUATOR_ENTITY
        )

        data: dict[str, Any] = {
            "status": "disabled",
            "actuator_mode": mode,
            "actuator_entity": ev_actuator_entity or None,
            "home_power_kw": None,
            "current_average_demand_kw": None,
            "maximum_demand_current_month_kw": None,
            "projected_peak_kw": None,
            "target_charge_current_limit_a": None,
            "target_charge_power_limit_kw": None,
            "resume_lockout_active": False,
            "resume_lockout_until": None,
            "apply_failed": False,
        }

        home_power_sensor = self._entry_text(CONF_HOME_POWER_SENSOR)
        if not home_power_sensor:
            data["status"] = "missing_home_power_sensor"
            self._log_control_state(
                status="missing_home_power_sensor",
                target=None,
                mode=mode,
                home_power_kw=None,
                current_average_demand_kw=None,
                projected_peak_kw=None,
                lockout_active=False,
                lockout_remaining=None,
            )
            return data

        home_power_kw = self._sensor_state_to_kw(home_power_sensor)
        data["home_power_kw"] = home_power_kw
        if home_power_kw is None:
            data["status"] = "home_power_unavailable"
            self._log_control_state(
                status="home_power_unavailable",
                target=None,
                mode=mode,
                home_power_kw=None,
                current_average_demand_kw=None,
                projected_peak_kw=None,
                lockout_active=False,
                lockout_remaining=None,
            )
            return data

        max_home_demand_kw = self._entry_float(CONF_MAX_HOME_DEMAND_KW, DEFAULT_MAX_HOME_DEMAND_KW)
        phase_count = max(1, min(self._entry_int(CONF_PHASE_COUNT, DEFAULT_PHASE_COUNT), 3))
        line_voltage_v = max(self._entry_float(CONF_LINE_VOLTAGE_V, DEFAULT_LINE_VOLTAGE_V), 1.0)

        current_average_demand_sensor = self._entry_text(CONF_CURRENT_AVERAGE_DEMAND_SENSOR)
        maximum_demand_sensor = self._entry_text(CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR)

        current_average_demand_kw: float | None = None
        if current_average_demand_sensor:
            current_average_demand_kw = self._sensor_state_to_kw(current_average_demand_sensor)
        data["current_average_demand_kw"] = current_average_demand_kw

        maximum_demand_current_month_kw: float | None = None
        if maximum_demand_sensor:
            maximum_demand_current_month_kw = self._sensor_state_to_kw(maximum_demand_sensor)
        data["maximum_demand_current_month_kw"] = maximum_demand_current_month_kw

        ev_actuator_value = self._state_float(ev_actuator_entity) if ev_actuator_entity else None
        if mode == ACTUATOR_MODE_CURRENT:
            ev_power_kw_estimate = (
                max((ev_actuator_value or 0.0) * line_voltage_v * phase_count / 1000.0, 0.0)
                if ev_actuator_value is not None
                else 0.0
            )
        else:
            ev_power_kw_estimate = max(ev_actuator_value or 0.0, 0.0)

        base_home_kw = max(home_power_kw - ev_power_kw_estimate, 0.0)
        dynamic_power_budget_kw = max(max_home_demand_kw, 0.0)
        allowed_ev_kw = max(dynamic_power_budget_kw - base_home_kw, 0.0)

        now = dt_util.now()
        status = "instant_limit"
        projected_peak_kw: float | None = None

        if current_average_demand_sensor:
            if current_average_demand_kw is None:
                status = "current_average_demand_unavailable"
            else:
                demand_kw = current_average_demand_kw
                self._update_demand_interval_on_falling_edge(now, demand_kw)

                interval_start = self._demand_interval_start or now
                if (now - interval_start) > timedelta(minutes=16):
                    interval_start = now
                    self._demand_interval_start = now

                elapsed_min = min(max((now - interval_start).total_seconds() / 60.0, 0.0), 15.0)
                remaining_min = max(15.0 - elapsed_min, 0.01)

                projected_peak_kw = (demand_kw + (home_power_kw * remaining_min / 15.0))
                data["projected_peak_kw"] = round(projected_peak_kw, 3)

                demand_limit_kw = dynamic_power_budget_kw
                if demand_kw >= demand_limit_kw:
                    allowed_ev_kw = 0.0
                    status = "demand_limit_reached"
                else:
                    target_total_kw = ((demand_limit_kw - demand_kw) * 15.0) / remaining_min
                    allowed_ev_kw_demand = max(target_total_kw - base_home_kw, 0.0)
                    if allowed_ev_kw_demand < allowed_ev_kw:
                        allowed_ev_kw = allowed_ev_kw_demand
                        status = "demand_guard"

        if self._resume_lockout_until is not None and now >= self._resume_lockout_until:
            self._resume_lockout_until = None

        is_paused = ev_actuator_value is not None and ev_actuator_value <= 0.01
        if (
            is_paused
            and home_power_kw >= max_home_demand_kw
            and self._resume_lockout_until is None
        ):
            if (
                self._demand_interval_start is not None
                and (now - self._demand_interval_start) <= timedelta(minutes=15)
            ):
                lockout_anchor = self._demand_interval_start
            else:
                lockout_anchor = now

            self._resume_lockout_until = lockout_anchor + timedelta(minutes=30)

        lockout_active = self._resume_lockout_until is not None and now < self._resume_lockout_until
        lockout_remaining = (
            (self._resume_lockout_until - now)
            if lockout_active and self._resume_lockout_until is not None
            else None
        )

        data["resume_lockout_active"] = lockout_active
        data["resume_lockout_until"] = self._resume_lockout_until if lockout_active else None

        if lockout_active:
            allowed_ev_kw = 0.0
            status = "resume_lockout"

        if not ev_actuator_entity:
            data["status"] = "missing_actuator_entity"
            self._log_control_state(
                status="missing_actuator_entity",
                target=None,
                mode=mode,
                home_power_kw=home_power_kw,
                current_average_demand_kw=current_average_demand_kw,
                projected_peak_kw=projected_peak_kw,
                lockout_active=lockout_active,
                lockout_remaining=lockout_remaining,
            )
            return data

        if mode == ACTUATOR_MODE_CURRENT:
            min_current_a = self._entry_float(CONF_MIN_CHARGE_CURRENT_A, DEFAULT_MIN_CHARGE_CURRENT_A)
            max_current_a = self._entry_float(CONF_MAX_CHARGE_CURRENT_A, DEFAULT_MAX_CHARGE_CURRENT_A)
            step_a = self._entry_float(CONF_CURRENT_STEP_A, DEFAULT_CURRENT_STEP_A)

            total_voltage = max(line_voltage_v * phase_count, 1.0)
            target_current_a = (allowed_ev_kw * 1000.0) / total_voltage
            target_current_a = min(max_current_a, max(0.0, target_current_a))
            if 0.0 < target_current_a < min_current_a:
                target_current_a = 0.0

            target_current_a = self._round_to_step(target_current_a, step_a)
            data["target_charge_current_limit_a"] = target_current_a

            should_apply = ev_actuator_value is None or abs(target_current_a - ev_actuator_value) >= max(step_a, 0.001)
            if should_apply:
                try:
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {"entity_id": ev_actuator_entity, "value": target_current_a},
                        blocking=True,
                    )
                except Exception as err:  # pragma: no cover - runtime-side service failures
                    _LOGGER.warning("Failed to set EV current actuator value on %s: %s", ev_actuator_entity, err)
                    data["apply_failed"] = True
                    status = "apply_failed"

            target_for_log: float | None = target_current_a
        else:
            max_power_kw = self._entry_float(CONF_MAX_CHARGE_POWER_KW, DEFAULT_MAX_CHARGE_POWER_KW)
            step_kw = self._entry_float(CONF_POWER_STEP_KW, DEFAULT_POWER_STEP_KW)

            target_power_kw = min(max_power_kw, max(0.0, allowed_ev_kw))
            target_power_kw = self._round_to_step(target_power_kw, step_kw)
            data["target_charge_power_limit_kw"] = target_power_kw

            should_apply = ev_actuator_value is None or abs(target_power_kw - ev_actuator_value) >= max(step_kw, 0.001)
            if should_apply:
                try:
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {"entity_id": ev_actuator_entity, "value": target_power_kw},
                        blocking=True,
                    )
                except Exception as err:  # pragma: no cover - runtime-side service failures
                    _LOGGER.warning("Failed to set EV power actuator value on %s: %s", ev_actuator_entity, err)
                    data["apply_failed"] = True
                    status = "apply_failed"

            target_for_log = target_power_kw

        data["status"] = status

        self._log_control_state(
            status=status,
            target=target_for_log,
            mode=mode,
            home_power_kw=home_power_kw,
            current_average_demand_kw=current_average_demand_kw,
            projected_peak_kw=projected_peak_kw,
            lockout_active=lockout_active,
            lockout_remaining=lockout_remaining,
        )

        return data
