"""Optional estimated EV charging cost from a user-selected price sensor."""
from __future__ import annotations

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .cost_math import CostEstimate, MAX_INTERVAL_SECONDS, normalize_rate, utc_timestamp
from .energy_helper import valid_sample

_CURRENT_STATE = object()


class HiveEVCostHelper(CoordinatorEntity, RestoreSensor):
    """A cumulative estimate; tariff credits may reduce the monetary total."""

    _attr_has_entity_name = True
    _attr_name = "Charging cost helper"
    _attr_icon = "mdi:cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_extra_state_attributes = {"estimated": True, "helper": True,
        "source": "Reported charging power and selected electricity rate",
        "method": "left interval cost estimate", "maximum_interval_seconds": MAX_INTERVAL_SECONDS}

    def __init__(self, coordinator, node_id, rate_entity, currency):
        super().__init__(coordinator)
        self._node_id = node_id
        self._rate_entity = rate_entity
        self._currency = currency
        self._estimate = CostEstimate()
        self._ready = False
        self._last_power_received = None
        self._attr_native_unit_of_measurement = currency
        self._attr_unique_id = f"{node_id}_cost_helper_{currency}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, node_id)},
            name=coordinator.data[node_id].name, manufacturer="Hive", model="EV charger")

    def _inputs(self, at, rate_state=_CURRENT_STATE):
        device = (self.coordinator.data or {}).get(self._node_id)
        state = self.hass.states.get(self._rate_entity) if rate_state is _CURRENT_STATE else rate_state
        price = normalize_rate(state.state, state.attributes.get("unit_of_measurement")) if state else None
        valid = (self.coordinator.last_update_success and device is not None
                 and valid_sample(device.power_w, device.last_updated) and utc_timestamp(at)
                 and 0 <= (at - device.last_updated).total_seconds() <= MAX_INTERVAL_SECONDS
                 and price is not None and price[0] == self._currency)
        return (device.power_w if device else None, price[1] if price else None, bool(valid))

    @property
    def available(self):
        return super().available and self._inputs(dt_util.utcnow())[2]

    @property
    def native_value(self):
        return self._estimate.total

    def _observe(self, at, rate_state=_CURRENT_STATE):
        power, rate, valid = self._inputs(at, rate_state)
        self._estimate.observe(power, rate, at, valid)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if restored is not None:
            self._estimate.restore(restored.native_value, restored.native_unit_of_measurement, self._currency)
        self._ready = True
        device = (self.coordinator.data or {}).get(self._node_id)
        if device and valid_sample(device.power_w, device.last_updated):
            self._last_power_received = device.last_updated
        self._observe(dt_util.utcnow())
        self.async_on_remove(async_track_state_change_event(self.hass, [self._rate_entity], self._rate_changed))

    @callback
    def _rate_changed(self, event):
        if self._ready:
            # Preserve each event's price and receipt time even when changes queue.
            at = event.time_fired if event is not None else dt_util.utcnow()
            state = event.data.get("new_state") if event is not None else _CURRENT_STATE
            self._observe(at, state)
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        if not self._ready:
            return
        device = (self.coordinator.data or {}).get(self._node_id)
        valid_power = (self.coordinator.last_update_success and device is not None
                       and valid_sample(device.power_w, device.last_updated))
        if valid_power:
            if self._last_power_received is not None:
                seconds = (device.last_updated - self._last_power_received).total_seconds()
                if seconds > MAX_INTERVAL_SECONDS or seconds < 0:
                    self._estimate.observe(None, None, None, False)
            self._last_power_received = device.last_updated
        else:
            self._last_power_received = None
        self._observe(device.last_updated if device else dt_util.utcnow())
        super()._handle_coordinator_update()
