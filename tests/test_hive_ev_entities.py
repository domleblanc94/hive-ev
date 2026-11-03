"""Entity behaviour checks using minimal HA interfaces on Windows.

These verify our values/lifecycle decisions, not full Home Assistant loading.
"""

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


@dataclass
class Description:
    key: str
    name: str = ""
    icon: str | None = None
    device_class: str | None = None
    entity_category: str | None = None
    native_unit_of_measurement: str | None = None
    state_class: str | None = None


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def async_added_to_hass(self):
        pass

    def _handle_coordinator_update(self):
        pass

    @property
    def available(self):
        return self.coordinator.last_update_success


def load_entity_modules():
    modules = {}
    def module(name, **attrs):
        obj = ModuleType(name)
        obj.__dict__.update(attrs)
        modules[name] = obj
        return obj

    module("homeassistant")
    module("homeassistant.components")
    class RestoreSensor:
        async def async_get_last_sensor_data(self):
            return None

    module("homeassistant.components.sensor", SensorEntity=type("SensorEntity", (), {}), RestoreSensor=RestoreSensor,
           SensorEntityDescription=Description,
           SensorDeviceClass=SimpleNamespace(POWER="power", ENERGY="energy", MONETARY="monetary", DURATION="duration", TIMESTAMP="timestamp"),
           SensorStateClass=SimpleNamespace(MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing", TOTAL="total"))
    module("homeassistant.components.binary_sensor", BinarySensorEntity=type("BinarySensorEntity", (), {}))
    module("homeassistant.const", UnitOfPower=SimpleNamespace(WATT="W"),
           UnitOfEnergy=SimpleNamespace(WATT_HOUR="Wh", KILO_WATT_HOUR="kWh"), UnitOfTime=SimpleNamespace(SECONDS="s"))
    module("homeassistant.core", callback=lambda f: f)
    module("homeassistant.helpers")
    module("homeassistant.helpers.event", async_track_state_change_event=lambda *args: (lambda: None))
    module("homeassistant.util", dt=SimpleNamespace(utcnow=lambda: datetime.now(timezone.utc)))
    module("homeassistant.helpers.entity", DeviceInfo=lambda **kw: kw,
           EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"))
    module("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity)
    root = Path(__file__).parents[1] / "custom_components" / "hive_ev"
    package = module("hive_ev_entity_test")
    package.__path__ = [str(root)]
    module("hive_ev_entity_test.const", DOMAIN="hive_ev", CONF_COST_RATE="electricity_rate_sensor", CONF_COST_CURRENCY="cost_currency")
    loaded = []
    with patch.dict(sys.modules, modules):
        for name in ("sensor", "binary_sensor"):
            spec = importlib.util.spec_from_file_location(f"hive_ev_entity_test.{name}", root / f"{name}.py")
            obj = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(obj)
            loaded.append(obj)
        loaded.append(sys.modules["hive_ev_entity_test.energy_helper"])
        loaded.append(sys.modules["hive_ev_entity_test.cost_helper"])
        loaded.append(sys.modules["hive_ev_entity_test.cost_math"])
    return loaded


sensor, binary, energy, cost, cost_math = load_entity_modules()


@dataclass
class Device:
    node_id: str = "test-node"
    home_id: str = "test-home"
    name: str = "Hive EV charger"
    status: str | None = "AVAILABLE"
    transaction_active: bool | None = False
    power_w: float | None = None
    session_energy_wh: float | None = None
    session_duration_s: float | None = None
    last_updated: datetime = datetime(2026, 10, 30, tzinfo=timezone.utc)


class Coordinator:
    def __init__(self, device):
        self.data = {device.node_id: device}
        self.last_update_success = True
        self.listeners = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)


class EntityTests(unittest.TestCase):
    def setUp(self):
        self.device = Device()
        self.coordinator = Coordinator(self.device)

    def entity(self, key):
        description = next(item for item in sensor.DESCRIPTIONS if item.key == key)
        return sensor.HiveEVSensor(self.coordinator, self.device.node_id, description)

    def test_available_does_not_imply_unplugged_or_charging(self):
        self.assertEqual(self.entity("status").native_value, "Available")
        entity = binary.HiveEVSessionSensor(self.coordinator, self.device.node_id)
        self.assertIs(entity.is_on, False)
        self.assertEqual(entity._attr_name, "Charging session active")

    def test_missing_measurements_and_session_activity_are_unknown(self):
        for key in ("power_w", "session_energy_wh", "session_duration_s"):
            self.assertIsNone(self.entity(key).native_value)
        self.coordinator.data[self.device.node_id] = replace(self.device, transaction_active=None)
        self.assertIsNone(binary.HiveEVSessionSensor(self.coordinator, self.device.node_id).is_on)

    def test_poll_failure_and_removed_device_are_unavailable(self):
        entities = [self.entity("status"), binary.HiveEVSessionSensor(self.coordinator, self.device.node_id)]
        self.coordinator.last_update_success = False
        self.assertTrue(all(not entity.available for entity in entities))
        self.coordinator.last_update_success = True
        self.coordinator.data = {}
        self.assertTrue(all(not entity.available for entity in entities))
        self.assertIsNone(entities[0].native_value)
        self.assertIsNone(entities[1].is_on)

    def test_session_resets_and_units_do_not_create_cumulative_statistics(self):
        entity = self.entity("session_energy_wh")
        self.coordinator.data[self.device.node_id] = replace(self.device, session_energy_wh=2300)
        self.assertEqual(entity.native_value, 2300)
        self.coordinator.data[self.device.node_id] = replace(self.device, session_energy_wh=0)
        self.assertEqual(entity.native_value, 0)
        self.assertEqual(entity.entity_description.native_unit_of_measurement, "Wh")
        self.assertIsNone(entity.entity_description.state_class)
        self.assertEqual(self.entity("session_duration_s").entity_description.native_unit_of_measurement, "s")
        self.assertEqual(self.entity("power_w").entity_description.native_unit_of_measurement, "W")

    def test_timestamp_is_receipt_time_and_ids_are_stable(self):
        self.assertEqual(self.entity("last_updated").native_value, self.device.last_updated)
        self.assertEqual(self.entity("status")._attr_unique_id, "test-node_status")

    def test_optional_telemetry_discovered_after_idle_setup_without_duplicates(self):
        entities, unload = [], []
        entry = SimpleNamespace(runtime_data=self.coordinator, async_on_unload=unload.append)
        asyncio.run(sensor.async_setup_entry(None, entry, entities.extend))
        self.assertEqual(len(entities), 2)
        self.coordinator.data[self.device.node_id] = replace(self.device, power_w=7200, session_energy_wh=0)
        for listener in self.coordinator.listeners:
            listener()
        self.assertEqual(len(entities), 5)
        for listener in self.coordinator.listeners:
            listener()
        self.assertEqual(len(entities), 5)
        unload[0]()
        self.assertEqual(self.coordinator.listeners, [])


if __name__ == "__main__":
    unittest.main()
