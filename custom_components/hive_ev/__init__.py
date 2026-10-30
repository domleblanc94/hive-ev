"""Read-only Hive EV monitoring through the existing Hive cloud connection."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HiveEVClient
from .coordinator import HiveEVCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up without touching charger configuration or schedules."""
    def save_tokens(tokens: dict) -> None:
        hass.config_entries.async_update_entry(entry, data={"tokens": tokens})

    client = HiveEVClient(async_get_clientsession(hass), entry.data["tokens"], save_tokens)
    coordinator = HiveEVCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
