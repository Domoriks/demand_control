"""Sensor platform for Demand Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DemandControlUpdateCoordinator


def _bool_to_on_off(value: Any) -> str | None:
    """Convert bool-like state to On/Off."""
    if value is None:
        return None
    return "On" if bool(value) else "Off"


def _as_datetime(value: Any) -> datetime | None:
    """Pass through datetime values used for timestamp sensors."""
    if isinstance(value, datetime):
        return value
    return None


@dataclass(frozen=True, kw_only=True)
class DemandControlSensorEntityDescription(SensorEntityDescription):
    """Extended sensor description with optional value conversion."""

    value_fn: Callable[[Any], StateType] | None = None


SENSOR_DEFINITIONS: tuple[DemandControlSensorEntityDescription, ...] = (
    DemandControlSensorEntityDescription(
        key="status",
        name="Status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="home_power_kw",
        name="Electricity Meter Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DemandControlSensorEntityDescription(
        key="current_average_demand_kw",
        name="Current Average Demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DemandControlSensorEntityDescription(
        key="maximum_demand_current_month_kw",
        name="Maximum Demand This Month",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="current_projected_demand_kw",
        name="Current Projected Demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="target_charge_current_limit_a",
        name="Target Charge Current Limit",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="target_charge_power_limit_kw",
        name="Target Charge Power Limit",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="lockout_active",
        name="Lockout Active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_bool_to_on_off,
    ),
    DemandControlSensorEntityDescription(
        key="lockout_until",
        name="Lockout Until",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_as_datetime,
    ),
    DemandControlSensorEntityDescription(
        key="actuator_mode",
        name="EV Actuator Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="actuator_entity",
        name="EV Actuator Entity",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DemandControlSensorEntityDescription(
        key="ev_power_kw",
        name="EV Actual Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


class DemandControlSensor(CoordinatorEntity[DemandControlUpdateCoordinator], SensorEntity):
    """Representation of a Demand Control sensor."""

    _attr_has_entity_name = True
    entity_description: DemandControlSensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DemandControlUpdateCoordinator,
        description: DemandControlSensorEntityDescription,
    ) -> None:
        """Initialize Demand Control sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value."""
        raw = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(raw)
        return raw  # type: ignore[return-value]

    @property
    def device_info(self) -> DeviceInfo:
        """Return metadata for this logical control device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="domoriks",
            model="Demand Control",
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Demand Control sensors for a config entry."""
    coordinator: DemandControlUpdateCoordinator = entry.runtime_data
    async_add_entities(
        DemandControlSensor(entry, coordinator, description)
        for description in SENSOR_DEFINITIONS
    )
