"""Hive EV monitoring with explicitly enrolled experimental controls."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HiveEVClient
from .coordinator import HiveEVCoordinator
from .controls import CONTROL_OPTIONS, HiveEVControlClient, controls_enabled

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up without touching charger configuration or schedules."""
    def save_tokens(tokens: dict) -> None:
        hass.config_entries.async_update_entry(entry, data={"tokens": tokens})

    client = HiveEVClient(async_get_clientsession(hass), entry.data["tokens"], save_tokens)
    coordinator = HiveEVCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    def disable_controls():
        options = dict(entry.options)
        options["enable_experimental_controls"] = False
        hass.config_entries.async_update_entry(entry, options=options)

    coordinator.controls = HiveEVControlClient(client, lambda: entry.options, disable_controls)
    coordinator.control_options = {key: entry.options.get(key) for key in CONTROL_OPTIONS}
    coordinator.loaded_platforms = PLATFORMS + ([Platform.BUTTON] if controls_enabled(entry.options) else [])
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_options))
    await hass.config_entries.async_forward_entry_setups(entry, coordinator.loaded_platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry.runtime_data.controls.invalidate()
    return await hass.config_entries.async_unload_platforms(entry, entry.runtime_data.loaded_platforms)


async def async_reload_options(hass, entry):
    current = {key: entry.options.get(key) for key in CONTROL_OPTIONS}
    if current != entry.runtime_data.control_options:
        entry.runtime_data.controls.invalidate()
        await hass.config_entries.async_reload(entry.entry_id)
