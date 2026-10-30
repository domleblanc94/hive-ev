"""Coordinate one reported-data poll every minute."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HiveEVAuthError, HiveEVClient, HiveEVDevice, HiveEVError
from .const import NAME, POLL_SECONDS

_LOGGER = logging.getLogger(__name__)


class HiveEVCoordinator(DataUpdateCoordinator[dict[str, HiveEVDevice]]):
    """Keep last values internally; failed updates make entities unavailable."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: HiveEVClient) -> None:
        super().__init__(hass, _LOGGER, name=NAME, config_entry=entry,
                         update_interval=timedelta(seconds=POLL_SECONDS))
        self.client = client

    async def _async_update_data(self) -> dict[str, HiveEVDevice]:
        try:
            return await self.client.async_devices()
        except HiveEVAuthError:
            raise ConfigEntryAuthFailed("Hive EV sign-in must be renewed") from None
        except HiveEVError:
            raise UpdateFailed("Hive EV monitoring could not be refreshed") from None
