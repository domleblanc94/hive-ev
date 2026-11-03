"""Optional cumulative Energy dashboard estimate from observed power intervals."""
from __future__ import annotations

from datetime import datetime, timedelta
import math

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

MAX_INTERVAL_SECONDS = 180


def valid_number(value):
    """Keep only finite, nonnegative readings, excluding Boolean values."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def valid_sample(power, received):
    """Power samples require an aware UTC receipt timestamp."""
    return (type(power) in (int, float) and valid_number(power) is not None
            and isinstance(received, datetime) and received.utcoffset() == timedelta(0))


class PowerEnergyEstimate:
    """Integrate the preceding power sample; never reconstruct missing history."""

    def __init__(self):
        self.total_kwh = 0.0
        self._baseline = None

    def restore(self, native_value, native_unit):
        value = valid_number(native_value)
        if native_unit == UnitOfEnergy.KILO_WATT_HOUR and value is not None:
            self.total_kwh = value
        self._baseline = None

    def observe(self, power, received, available=True):
        if not available or not valid_sample(power, received):
            self._baseline = None
            return
        power = float(power)
        if self._baseline is not None:
            previous_time, previous_power = self._baseline
            seconds = (received - previous_time).total_seconds()
            if seconds <= 0:
                return
            if seconds <= MAX_INTERVAL_SECONDS:
                total = self.total_kwh + previous_power * (seconds / 3_600_000)
                if math.isfinite(total):
                    self.total_kwh = total
        self._baseline = (received, power)


class HiveEVEnergyDashboardHelper(CoordinatorEntity, RestoreSensor):
    """An explicitly enabled power-derived estimate, not a charger meter total."""

    _attr_has_entity_name = True
    _attr_name = "Energy dashboard helper"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_entity_registry_enabled_default = False
    _attr_extra_state_attributes = {"estimated": True, "helper": True,
        "source": "Reported charging power", "method": "left interval power estimate",
        "maximum_interval_seconds": MAX_INTERVAL_SECONDS}

    def __init__(self, coordinator, node_id):
        super().__init__(coordinator)
        self._node_id = node_id
        self._estimate = PowerEnergyEstimate()
        self._ready = False
        self._attr_unique_id = f"{node_id}_energy_dashboard_helper"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, node_id)},
            name=coordinator.data[node_id].name, manufacturer="Hive", model="EV charger")

    @property
    def available(self):
        device = (self.coordinator.data or {}).get(self._node_id)
        return (super().available and device is not None
                and valid_sample(device.power_w, device.last_updated))

    @property
    def native_value(self):
        return self._estimate.total_kwh

    def _observe(self):
        device = (self.coordinator.data or {}).get(self._node_id)
        self._estimate.observe(device.power_w if device else None,
            device.last_updated if device else None, self.coordinator.last_update_success)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if restored is not None:
            self._estimate.restore(restored.native_value, restored.native_unit_of_measurement)
        self._ready = True
        self._observe()

    @callback
    def _handle_coordinator_update(self):
        if not self._ready:
            return
        self._observe()
        super()._handle_coordinator_update()
