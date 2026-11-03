"""Read-only Hive EV reported values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_COST_RATE, CONF_COST_CURRENCY
from .cost_helper import HiveEVCostHelper
from .energy_helper import HiveEVEnergyDashboardHelper, valid_sample

if TYPE_CHECKING:
    from .coordinator import HiveEVCoordinator

DESCRIPTIONS = (
    SensorEntityDescription(key="status", name="Charging status", icon="mdi:ev-station"),
    SensorEntityDescription(
        key="last_updated", name="Last successful refresh",
        device_class=SensorDeviceClass.TIMESTAMP, entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="power_w", name="Charging power", device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT, state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="session_energy_wh", name="Session energy", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        # A new charging session resets this reading. Do not aggregate session totals.
    ),
    SensorEntityDescription(
        key="session_duration_s", name="Session charging duration",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add telemetry when first reported, including after an idle installation."""
    coordinator = entry.runtime_data
    added: set[tuple[str, str]] = set()

    @callback
    def discover_entities():
        entities = []
        for node_id, device in (coordinator.data or {}).items():
            for description in DESCRIPTIONS:
                identity = (node_id, description.key)
                if identity in added:
                    continue
                if description.key not in ("status", "last_updated") and getattr(device, description.key) is None:
                    continue
                added.add(identity)
                entities.append(HiveEVSensor(coordinator, node_id, description))
            identity = (node_id, "energy_dashboard_helper")
            if identity not in added and valid_sample(device.power_w, device.last_updated):
                added.add(identity)
                entities.append(HiveEVEnergyDashboardHelper(coordinator, node_id))
            rate_entity = entry.options.get(CONF_COST_RATE) if hasattr(entry, "options") else None
            currency = entry.options.get(CONF_COST_CURRENCY) if hasattr(entry, "options") else None
            identity = (node_id, "cost_helper")
            if rate_entity and currency and identity not in added:
                added.add(identity)
                entities.append(HiveEVCostHelper(coordinator, node_id, rate_entity, currency))
        if entities:
            async_add_entities(entities)

    discover_entities()
    entry.async_on_unload(coordinator.async_add_listener(discover_entities))


class HiveEVSensor(CoordinatorEntity, SensorEntity):
    """One reported value; missing telemetry remains unknown."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HiveEVCoordinator, node_id: str, description: SensorEntityDescription):
        super().__init__(coordinator)
        self._node_id = node_id
        self.entity_description = description
        self._attr_unique_id = f"{node_id}_{description.key}"
        device = coordinator.data[node_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, node_id)}, name=device.name,
            manufacturer="Hive", model="EV charger",
        )

    @property
    def available(self):
        return super().available and self._node_id in (self.coordinator.data or {})

    @property
    def native_value(self):
        device = (self.coordinator.data or {}).get(self._node_id)
        if device is None:
            return None
        value = getattr(device, self.entity_description.key)
        if self.entity_description.key == "status" and value is not None:
            return value.replace("_", " ").capitalize()
        return value
