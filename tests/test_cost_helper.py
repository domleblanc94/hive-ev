"""Synthetic provider-neutral cost, option and lifecycle checks; no account calls."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_hive_ev_entities import Coordinator, Device, sensor, cost as helper, cost_math as math
from test_hive_ev_core import flow_module

START = datetime(2026, 11, 3, tzinfo=timezone.utc)


def price(value="0.25", unit="GBP/kWh"):
    return SimpleNamespace(state=value, attributes={"unit_of_measurement": unit})


class CurrencyAndMathTests(unittest.TestCase):
    def test_explicit_currency_aliases_and_scaling(self):
        for value, unit, expected in ((25, "p/kWh", ("GBP", .25)), (25, "GBp/kWh", ("GBP", .25)),
                (25, "pence/kWh", ("GBP", .25)), (.25, "£/kWh", ("GBP", .25)),
                (250, "EUR/MWh", ("EUR", .25)), (.3, "USD/kWh", ("USD", .3)),
                (-10, "GBP/MWh", ("GBP", -.01)), (.25, "€/kWh", ("EUR", .25))):
            self.assertEqual(math.normalize_rate(value, unit), expected)

    def test_ambiguous_unsupported_and_nonfinite_tariffs_rejected(self):
        for value, unit in ((1, "$/kWh"), (1, "c/kWh"), (1, "XXX/kWh"),
                (1, "GBP"), (1, "GBP/Wh"), (1, None), (True, "GBP/kWh"),
                ("unknown", "GBP/kWh"), ("inf", "GBP/kWh"), (float("nan"), "GBP/kWh")):
            self.assertIsNone(math.normalize_rate(value, unit))

    def test_rate_boundary_splits_cost_and_allows_negative_credit(self):
        estimate = math.CostEstimate()
        estimate.observe(6000, .1, START)
        estimate.observe(6000, .3, START + timedelta(seconds=30))
        estimate.observe(6000, -.1, START + timedelta(seconds=60))
        self.assertAlmostEqual(estimate.total, .02)
        estimate.observe(0, -.1, START + timedelta(seconds=120))
        self.assertAlmostEqual(estimate.total, .01)

    def test_same_timestamp_replaces_baseline_without_double_charge(self):
        estimate = math.CostEstimate()
        estimate.observe(6000, .1, START)
        estimate.observe(6000, .3, START)
        estimate.observe(0, .3, START + timedelta(seconds=60))
        self.assertAlmostEqual(estimate.total, .03)

    def test_gap_unknown_and_regressive_observations_never_backfill(self):
        estimate = math.CostEstimate()
        estimate.observe(6000, .1, START)
        estimate.observe(0, .9, START - timedelta(seconds=1))
        estimate.observe(6000, .2, START + timedelta(seconds=300))
        self.assertEqual(estimate.total, 0)
        estimate.observe(None, .2, START + timedelta(seconds=310))
        estimate.observe(6000, .2, START + timedelta(seconds=320))
        self.assertEqual(estimate.total, 0)
        estimate.observe(0, .2, START + timedelta(seconds=380))
        self.assertAlmostEqual(estimate.total, .02)

    def test_restore_signed_total_only_same_currency_and_finite(self):
        for value, unit, wanted in ((-2, "GBP", -2), (10, "EUR", 0),
                (True, "GBP", 0), (float("inf"), "GBP", 0)):
            estimate = math.CostEstimate()
            estimate.restore(value, unit, "GBP")
            estimate.observe(6000, .1, START + timedelta(days=1))
            self.assertEqual(estimate.total, wanted)


class CostEntityTests(unittest.IsolatedAsyncioTestCase):
    async def entity(self, rate=None):
        device = Device(power_w=6000, last_updated=START)
        coordinator = Coordinator(device)
        entity = helper.HiveEVCostHelper(coordinator, device.node_id, "sensor.invented_price", "GBP")
        entity.hass = SimpleNamespace(states=SimpleNamespace(get=Mock(return_value=rate or price())))
        entity.async_get_last_sensor_data = AsyncMock(return_value=SimpleNamespace(native_value=10, native_unit_of_measurement="GBP"))
        entity.async_on_remove = Mock()
        entity.async_write_ha_state = Mock()
        with patch.object(helper.dt_util, "utcnow", return_value=START):
            await entity.async_added_to_hass()
        return device, coordinator, entity

    async def test_monetry_metadata_restore_and_no_offline_fill(self):
        device, coordinator, entity = await self.entity()
        self.assertEqual(entity._attr_device_class, "monetary")
        self.assertEqual(entity._attr_state_class, "total")
        self.assertEqual(entity._attr_native_unit_of_measurement, "GBP")
        self.assertEqual(entity._attr_unique_id, "test-node_cost_helper_GBP")
        self.assertEqual(entity.native_value, 10)
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=60))
        entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, 10.025)

    async def test_rate_event_splits_cost_and_discovery_does_not_use_session_total(self):
        device, coordinator, entity = await self.entity(price("0.1"))
        entity.hass.states.get.return_value = price("0.3")
        with patch.object(helper.dt_util, "utcnow", return_value=START + timedelta(seconds=30)):
            entity._rate_changed(None)
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=60), session_energy_wh=0)
        entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, 10.02)

    async def test_queued_price_events_use_event_state_not_latest_state(self):
        device, coordinator, entity = await self.entity(price("0.1"))
        entity.hass.states.get.return_value = price("0.9")
        event = SimpleNamespace(time_fired=START + timedelta(seconds=30),
                                data={"new_state": price("0.3")})
        entity._rate_changed(event)
        event = SimpleNamespace(time_fired=START + timedelta(seconds=60),
                                data={"new_state": price("0.9")})
        entity._rate_changed(event)
        self.assertAlmostEqual(entity.native_value, 10.02)

    async def test_rate_events_cannot_extend_old_power_through_poll_gap(self):
        device, coordinator, entity = await self.entity()
        with patch.object(helper.dt_util, "utcnow", return_value=START + timedelta(seconds=170)):
            entity._rate_changed(None)
        total = entity.native_value
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=300))
        entity._handle_coordinator_update()
        self.assertEqual(entity.native_value, total)
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=360))
        entity._handle_coordinator_update()
        self.assertAlmostEqual(entity.native_value, total + .025)

    async def test_currency_drift_missing_price_and_failed_power_are_unavailable(self):
        device, coordinator, entity = await self.entity()
        for state in (price(".2", "EUR/kWh"), price("unavailable"), None):
            entity.hass.states.get.return_value = state
            with patch.object(helper.dt_util, "utcnow", return_value=START + timedelta(seconds=30)):
                self.assertFalse(entity.available)
                entity._rate_changed(None)
        entity.hass.states.get.return_value = price()
        coordinator.last_update_success = False
        entity._handle_coordinator_update()
        coordinator.last_update_success = True
        coordinator.data[device.node_id] = replace(device, last_updated=START + timedelta(seconds=60))
        entity._handle_coordinator_update()
        self.assertEqual(entity.native_value, 10)


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    def flow(self, current=None, state=None):
        flow = flow_module.HiveEVOptionsFlow()
        flow.config_entry = SimpleNamespace(options=current or {}, runtime_data=SimpleNamespace(data={"one": object()}))
        flow.hass = SimpleNamespace(states=SimpleNamespace(get=Mock(return_value=state)))
        return flow

    async def test_optional_rate_enrollment_and_remove_preserve_other_options(self):
        current = {"enable_experimental_controls": True, "owner_confirmed_alfen": True, "future_option": "keep"}
        flow = self.flow(current, price("25", "p/kWh"))
        form = await flow.async_step_init()
        defaults = form["data_schema"]({})
        self.assertTrue(defaults["enable_experimental_controls"])
        result = await flow.async_step_init({"electricity_rate_sensor": "sensor.generic_rate"})
        self.assertEqual(result["data"]["cost_currency"], "GBP")
        self.assertEqual(result["data"]["future_option"], "keep")
        self.assertTrue(result["data"]["enable_experimental_controls"])
        flow.config_entry.options = result["data"]
        removed = await flow.async_step_init({"remove_cost_helper": True})
        self.assertNotIn("electricity_rate_sensor", removed["data"])
        self.assertNotIn("cost_currency", removed["data"])
        self.assertTrue(removed["data"]["enable_experimental_controls"])

    async def test_invalid_new_rate_rejected_but_enrolled_unavailable_retained(self):
        flow = self.flow(state=price(".1", "$/kWh"))
        result = await flow.async_step_init({"electricity_rate_sensor": "sensor.generic_rate"})
        self.assertEqual(result["errors"]["base"], "invalid_rate_sensor")
        current = {"electricity_rate_sensor": "sensor.generic_rate", "cost_currency": "GBP"}
        flow = self.flow(current, price("unavailable"))
        result = await flow.async_step_init({"electricity_rate_sensor": "sensor.generic_rate"})
        self.assertEqual(result["data"], current)

    async def test_explicit_reconfigure_same_sensor_new_currency(self):
        current = {"electricity_rate_sensor": "sensor.generic_rate", "cost_currency": "GBP"}
        result = await self.flow(current, price(".3", "EUR/kWh")).async_step_init({"electricity_rate_sensor": "sensor.generic_rate"})
        self.assertEqual(result["data"]["cost_currency"], "EUR")
