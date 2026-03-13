"""Switch platform for Demand Control — pause / resume charger control."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DemandControlUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Demand Control switch."""
    coordinator: DemandControlUpdateCoordinator = entry.runtime_data
    async_add_entities([DemandControlSwitch(entry, coordinator)])


class DemandControlSwitch(
    CoordinatorEntity[DemandControlUpdateCoordinator], SwitchEntity, RestoreEntity
):
    """Switch to enable or pause EV charger demand control.

    ON  → control active: coordinator calculates targets AND writes to the actuator.
    OFF → control paused: coordinator still calculates projected demand but does NOT
          write any value to the actuator entity.
    """

    _attr_has_entity_name = True
    _attr_name = "EV Charge Control"
    _attr_icon = "mdi:ev-station"

    def __init__(
        self, entry: ConfigEntry, coordinator: DemandControlUpdateCoordinator
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_control_enabled"
        self._is_on: bool = True

    async def async_added_to_hass(self) -> None:
        """Restore previous state on restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state != STATE_OFF
            self.coordinator.control_enabled = self._is_on

    @property
    def is_on(self) -> bool:
        """Return True when demand control is active."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """Enable demand control — coordinator will write to the actuator."""
        self._is_on = True
        self.coordinator.control_enabled = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        """Pause demand control — coordinator will only calculate, not write."""
        self._is_on = False
        self.coordinator.control_enabled = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return metadata linking this entity to the Demand Control device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="domoriks",
            model="Demand Control",
        )
