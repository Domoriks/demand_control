"""The Demand Control integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import DemandControlUpdateCoordinator


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Demand Control integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Demand Control from a config entry."""
    coordinator = DemandControlUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Demand Control config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
