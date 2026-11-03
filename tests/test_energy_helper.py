"""Power-derived energy estimates: no meter totals, session sums or gap filling."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from test_hive_ev_entities import Coordinator, Device, energy, sensor

START = datetime(2026, 11, 3, tzinfo=timezone.utc)


class EstimateTests(unittest.TestCase):
    def test_left_interval_estimate_and_session_independence(self):
        estimate = energy.PowerEnergyEstimate()
        estimate.observe(7000, START)
        self.assertEqual(estimate.total_kwh, 0)
        estimate.observe(0, START + timedelta(seconds=60))
        self.assertAlmostEqual(estimate.total_kwh, 7 / 60)
        estimate.observe(7000, START + timedelta(seconds=120))
        self.assertAlmostEqual(estimate.total_kwh, 7 / 60)
        estimate.observe(0, START + timedelta(seconds=180))
        self.assertAlmostEqual(estimate.total_kwh, 14 / 60)

    def test_restore_preserves_total_but_never_restores_baseline(self):
        estimate = energy.PowerEnergyEstimate()
        estimate.restore(12.5, "kWh")
        estimate.observe(7000, START + timedelta(days=2))
        self.assertEqual(estimate.total_kwh, 12.5)
        estimate.observe(7000, START + timedelta(days=2, seconds=60))
        self.assertAlmostEqual(estimate.total_kwh, 12.5 + 7 / 60)

    def test_restore_rejects_wrong_units_bad_values_and_boolean(self):
        for value, unit in ((1000, "Wh"), (1, None), (-1, "kWh"), (float("nan"), "kWh"),
                            (float("inf"), "kWh"), (True, "kWh"), ("unknown", "kWh"), (10**1000, "kWh")):
            estimate = energy.PowerEnergyEstimate()
            estimate.restore(value, unit)
            self.assertEqual(estimate.total_kwh, 0)

    def test_missing_invalid_failure_and_naive_timestamp_reset_baseline(self):
        for invalid in (None, -1, True, "7000", float("nan"), float("inf"), 10**1000):
            estimate = energy.PowerEnergyEstimate()
            estimate.observe(7000, START)
            estimate.observe(invalid, START + timedelta(seconds=60))
            estimate.observe(7000, START + timedelta(seconds=120))
            self.assertEqual(estimate.total_kwh, 0)
        for available, stamp in ((False, START + timedelta(seconds=60)),
                                 (True, START.replace(tzinfo=None)), (True, None)):
            estimate = energy.PowerEnergyEstimate()
            estimate.observe(7000, START)
            estimate.observe(7000, stamp, available)
            estimate.observe(7000, START + timedelta(seconds=120))
            self.assertEqual(estimate.total_kwh, 0)

    def test_long_gap_is_not_integrated_but_fresh_following_interval_is(self):
        estimate = energy.PowerEnergyEstimate()
        estimate.observe(7000, START)
        estimate.observe(7000, START + timedelta(hours=3))
        self.assertEqual(estimate.total_kwh, 0)
        estimate.observe(0, START + timedelta(hours=3, seconds=60))
        self.assertAlmostEqual(estimate.total_kwh, 7 / 60)

    def test_duplicate_regressive_intervals_do_not_change_baseline_or_total(self):
        estimate = energy.PowerEnergyEstimate()
        estimate.observe(7000, START)
        estimate.observe(0, START)
        estimate.observe(0, START - timedelta(seconds=60))
        estimate.observe(0, START + timedelta(seconds=60))
        self.assertAlmostEqual(estimate.total_kwh, 7 / 60)

    def test_independent_devices_do_not_share_totals(self):
        one, two = energy.PowerEnergyEstimate(), energy.PowerEnergyEstimate()
        one.observe(7000, START)
        two.observe(3000, START)
        one.observe(0, START + timedelta(seconds=60))
        two.observe(0, START + timedelta(seconds=60))
        self.assertAlmostEqual(one.total_kwh, 7 / 60)
        self.assertAlmostEqual(two.total_kwh, 3 / 60)


class HelperEntityTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_restore_and_no_offline_backfill(self):
        device = Device(power_w=7000, last_updated=START)
        coordinator = Coordinator(device)
        entity = energy.HiveEVEnergyDashboardHelper(coordinator, device.node_id)
        entity.async_get_last_sensor_data = AsyncMock(return_value=SimpleNamespace(native_value=10, native_unit_of_measurement="kWh"))
        await entity.async_added_to_hass()
        self.assertFalse(entity._attr_entity_registry_enabled_default)
        self.assertEqual(entity._attr_device_class, "energy")
        self.assertEqual(entity._attr_state_class, "total_increasing")
        self.assertEqual(entity._attr_native_unit_of_measurement, "kWh")
        self.assertEqual(entity._attr_unique_id, "test-node_energy_dashboard_helper")
        self.assertTrue(entity._attr_extra_state_attributes["estimated"])
        self.assertEqual(entity.native_value, 10)
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=60), session_energy_wh=0)
        entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, 10 + 7 / 60)

    async def test_availability_failure_removal_and_missing_power_no_backfill(self):
        device = Device(power_w=7000, last_updated=START)
        coordinator = Coordinator(device)
        entity = energy.HiveEVEnergyDashboardHelper(coordinator, device.node_id)
        await entity.async_added_to_hass()
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=60))
        entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, 7 / 60)
        coordinator.last_update_success = False
        entity._handle_coordinator_update()
        self.assertFalse(entity.available)
        coordinator.last_update_success = True
        coordinator.data = {}
        entity._handle_coordinator_update()
        self.assertFalse(entity.available)
        coordinator.data = {device.node_id: replace(device, power_w=None, last_updated=START + timedelta(seconds=120))}
        entity._handle_coordinator_update()
        self.assertFalse(entity.available)
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=180))
        entity._handle_coordinator_update()
        self.assertTrue(entity.available)
        self.assertAlmostEqual(entity.native_value, 7 / 60)

    async def test_session_meter_reset_never_resets_or_adds_to_helper_total(self):
        device = Device(power_w=7000, session_energy_wh=1000, last_updated=START)
        coordinator = Coordinator(device)
        entity = energy.HiveEVEnergyDashboardHelper(coordinator, device.node_id)
        await entity.async_added_to_hass()
        for seconds, power, session_wh in ((60, 0, 2000), (120, 0, 0), (180, 7000, 0), (240, 0, 30)):
            coordinator.data[device.node_id] = replace(device, power_w=power,
                session_energy_wh=session_wh, last_updated=START + timedelta(seconds=seconds))
            entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, 14 / 60)

    async def test_optional_helper_added_once_only_when_valid_power_known(self):
        device = Device(last_updated=START)
        coordinator = Coordinator(device)
        entities = []
        entry = SimpleNamespace(runtime_data=coordinator, async_on_unload=lambda callback: None)
        await sensor.async_setup_entry(None, entry, entities.extend)
        self.assertFalse(any(isinstance(item, energy.HiveEVEnergyDashboardHelper) for item in entities))
        coordinator.data[device.node_id] = replace(device, power_w=0)
        for listener in coordinator.listeners:
            listener()
        for listener in coordinator.listeners:
            listener()
        helpers = [item for item in entities if isinstance(item, energy.HiveEVEnergyDashboardHelper)]
        self.assertEqual(len(helpers), 1)
        self.assertFalse(helpers[0]._attr_entity_registry_enabled_default)
