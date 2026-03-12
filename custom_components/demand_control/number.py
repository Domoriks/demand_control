"""Number platform for Demand Control option entities."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAX_CHARGE_CURRENT_A,
    CONF_MAX_CHARGE_POWER_KW,
    CONF_MAX_HOME_DEMAND_KW,
    DEFAULT_MAX_CHARGE_CURRENT_A,
    DEFAULT_MAX_CHARGE_POWER_KW,
    DEFAULT_MAX_HOME_DEMAND_KW,
    DOMAIN,
)
from .coordinator import DemandControlUpdateCoordinator


class DemandControlOptionNumber(CoordinatorEntity[DemandControlUpdateCoordinator], NumberEntity):
    """Base class for Demand Control options persisted in entry options."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _option_key: str
    _default_value: float

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DemandControlUpdateCoordinator,
        unique_id_suffix: str,
    ) -> None:
        """Initialize option number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"

    @property
    def native_value(self) -> float:
        """Return current option value."""
        value = self._entry.options.get(self._option_key, self._entry.data.get(self._option_key))
        try:
            return float(value)
        except (TypeError, ValueError):
            return self._default_value

    async def async_set_native_value(self, value: float) -> None:
        """Persist updated option value and refresh coordinator."""
        updated_options = {**self._entry.options, self._option_key: float(value)}
        self.hass.config_entries.async_update_entry(self._entry, options=updated_options)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return metadata for this logical control device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="domoriks",
            model="Demand Control",
        )


class DemandControlMaxHomeDemand(DemandControlOptionNumber):
    """Configurable maximum home demand budget in kW."""

    _attr_name = "Max Home Demand"
    _attr_native_unit_of_measurement = "kW"
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER
    _option_key = CONF_MAX_HOME_DEMAND_KW
    _default_value = DEFAULT_MAX_HOME_DEMAND_KW

    def __init__(self, entry: ConfigEntry, coordinator: DemandControlUpdateCoordinator) -> None:
        """Initialize max home demand number."""
        super().__init__(entry, coordinator, "max_home_demand_kw")


class DemandControlMaxChargeCurrent(DemandControlOptionNumber):
    """Configurable upper bound for current-based actuation."""

    _attr_name = "Max Charge Current"
    _attr_native_unit_of_measurement = "A"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _option_key = CONF_MAX_CHARGE_CURRENT_A
    _default_value = DEFAULT_MAX_CHARGE_CURRENT_A

    def __init__(self, entry: ConfigEntry, coordinator: DemandControlUpdateCoordinator) -> None:
        """Initialize max charge current number."""
        super().__init__(entry, coordinator, "max_charge_current_a")


class DemandControlMaxChargePower(DemandControlOptionNumber):
    """Configurable upper bound for power-based actuation."""

    _attr_name = "Max Charge Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_min_value = 0.0
    _attr_native_max_value = 200.0
    _attr_native_step = 0.1
    _option_key = CONF_MAX_CHARGE_POWER_KW
    _default_value = DEFAULT_MAX_CHARGE_POWER_KW

    def __init__(self, entry: ConfigEntry, coordinator: DemandControlUpdateCoordinator) -> None:
        """Initialize max charge power number."""
        super().__init__(entry, coordinator, "max_charge_power_kw")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Demand Control number entities from config entry."""
    coordinator: DemandControlUpdateCoordinator = entry.runtime_data
    async_add_entities(
        [
            DemandControlMaxHomeDemand(entry, coordinator),
            DemandControlMaxChargeCurrent(entry, coordinator),
            DemandControlMaxChargePower(entry, coordinator),
        ]
    )
