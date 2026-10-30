"""Read-only Hive EV charging-session indicator."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Represent reported session activity without inferring cable connection."""
    coordinator = entry.runtime_data
    added: set[str] = set()

    @callback
    def discover_entities():
        new_ids = set(coordinator.data or {}) - added
        if new_ids:
            async_add_entities([HiveEVSessionSensor(coordinator, node_id) for node_id in sorted(new_ids)])
            added.update(new_ids)

    discover_entities()
    entry.async_on_unload(coordinator.async_add_listener(discover_entities))


class HiveEVSessionSensor(CoordinatorEntity, BinarySensorEntity):
    """Whether Hive reports an active transaction, independent of power draw."""

    _attr_has_entity_name = True
    _attr_name = "Charging session active"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, node_id: str):
        super().__init__(coordinator)
        self._node_id = node_id
        self._attr_unique_id = f"{node_id}_session_active"
        device = coordinator.data[node_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, node_id)}, name=device.name,
            manufacturer="Hive", model="EV charger",
        )

    @property
    def available(self):
        return super().available and self._node_id in (self.coordinator.data or {})

    @property
    def is_on(self):
        device = (self.coordinator.data or {}).get(self._node_id)
        return device.transaction_active if device is not None else None
