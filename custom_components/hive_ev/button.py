"""Explicitly enrolled, experimental Alfen buttons."""
from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HiveEVError
from .const import DOMAIN
from .controls import controls_enabled


async def async_setup_entry(hass, entry, async_add_entities):
    if not controls_enabled(entry.options):
        return
    coordinator = entry.runtime_data
    async_add_entities(ExperimentalButton(coordinator, node_id, action, name)
        for node_id in (coordinator.data or {})
        for action, name in (("charge_now", "Charge now (experimental)"),
                             ("end_session", "End charging session (experimental)")))


class ExperimentalButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, node_id, action, name):
        super().__init__(coordinator)
        self.node_id = node_id
        self.action = action
        self._attr_name = name
        self._attr_unique_id = f"{node_id}_experimental_{action}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, node_id)},
            name=coordinator.data[node_id].name, manufacturer="Hive")

    @property
    def available(self):
        return super().available and controls_enabled(self.coordinator.controls.options) and self.node_id in (self.coordinator.data or {})

    async def async_press(self):
        device = (self.coordinator.data or {}).get(self.node_id)
        if device is None:
            raise HomeAssistantError("Charger monitoring is unavailable.")
        try:
            message = await self.coordinator.controls.async_command(device, self.action)
        except HiveEVError as error:
            raise HomeAssistantError(str(error)) from None
        persistent_notification.async_create(self.hass, message,
            title="Hive EV experimental command: check Hive and car")
        await self.coordinator.async_request_refresh()
