"""Synthetic tests: no network, credentials or physical charger commands."""
import asyncio
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_hive_ev_core import PKG, Response, api, flow_module, tokens

controls = importlib.import_module(f"{PKG}.controls")
OPTIONS = {key: True for key in controls.CONTROL_OPTIONS}
DEVICE = SimpleNamespace(node_id="invented-node", home_id="invented-home")


def node(action="charge_now"):
    values = {"displayState": "SCHEDULED", "scheduleMode": "TARIFF",
              "transactionActive": True, "transactionOverridden": False,
              "transactionActivePowerImportW": 0}
    if action == "end_session":
        values.update(displayState="CHARGING", transactionOverridden=True,
                      transactionActivePowerImportW=1200)
    return {"id": DEVICE.node_id, "nodeType": controls.EVSE_TYPE,
            "features": {controls.FEATURE: {key: {"reportedValue": value}
                                             for key, value in values.items()}}}


class GuardTests(unittest.TestCase):
    def test_both_actions_require_settled_reported_state(self):
        for action in ("charge_now", "end_session"):
            controls.check_guard(node(action), action)
            for key, bad in (("scheduleMode", "DSR"), ("transactionActive", False),
                             ("transactionActivePowerImportW", None)):
                changed = node(action)
                changed["features"][controls.FEATURE][key]["reportedValue"] = bad
                with self.assertRaises(controls.HiveEVControlError):
                    controls.check_guard(changed, action)
            for key in node(action)["features"][controls.FEATURE]:
                changed = node(action)
                changed["features"][controls.FEATURE][key]["propertyStatus"] = "PENDING"
                with self.assertRaises(controls.HiveEVControlError):
                    controls.check_guard(changed, action)

    def test_positive_power_denies_start_and_zero_denies_end(self):
        for action, power in (("charge_now", 1), ("end_session", 0)):
            changed = node(action)
            changed["features"][controls.FEATURE]["transactionActivePowerImportW"]["reportedValue"] = power
            with self.assertRaises(controls.HiveEVControlError):
                controls.check_guard(changed, action)

    def test_target_only_or_contradictory_values_never_authorize(self):
        for action in ("charge_now", "end_session"):
            changed = node(action)
            changed["features"][controls.FEATURE]["transactionOverridden"]["targetValue"] = action == "charge_now"
            with self.assertRaises(controls.HiveEVControlError):
                controls.check_guard(changed, action)
        self.assertFalse(controls.controls_enabled({}))
        self.assertFalse(controls.controls_enabled({"enable_experimental_controls": True}))

    def test_pending_or_requested_cable_unlock_denies_start(self):
        for wrapper in ({"targetValue": True}, {"reportedValue": False, "targetValue": True},
                        {"reportedValue": False, "propertyStatus": "PENDING"}, {"reportedValue": True}):
            changed = node()
            changed["features"][controls.FEATURE]["cableUnlock"] = wrapper
            with self.assertRaises(controls.HiveEVControlError):
                controls.check_guard(changed, "charge_now")

    def test_malformed_unhashable_state_has_only_fixed_error(self):
        changed = node()
        changed["features"][controls.FEATURE]["displayState"]["reportedValue"] = {"private": ["data"]}
        with self.assertRaises(controls.HiveEVControlError) as error:
            controls.check_guard(changed, "charge_now")
        self.assertNotIn("private", str(error.exception))


class CommandTests(unittest.IsolatedAsyncioTestCase):
    def client(self, action="charge_now", response=None, options=None):
        session = SimpleNamespace(put=Mock(return_value=response or Response(200)))
        client = api.HiveEVClient(session, tokens())
        client._get = AsyncMock(return_value={"nodes": [node(action)]})
        client.async_devices = AsyncMock(return_value={DEVICE.node_id: DEVICE})
        disable = Mock()
        control = controls.HiveEVControlClient(client, OPTIONS if options is None else options, disable)
        return control, client, session, disable

    async def test_exact_literal_host_one_put_and_no_write_api_key(self):
        for action, attribute in (("charge_now", "transactionOverridden"), ("end_session", "cableUnlock")):
            control, client, session, _ = self.client(action)
            result = await control.async_command(DEVICE, action)
            self.assertIn("unconfirmed", result)
            client.async_devices.assert_awaited_once()
            client._get.assert_awaited_once()
            session.put.assert_called_once()
            url = session.put.call_args.args[0]
            self.assertEqual(url, "https://api-prod.bgchprod.info/omnia/nodes/invented-node?homeId=invented-home")
            kwargs = session.put.call_args.kwargs
            self.assertEqual(kwargs["json"], {"nodes": [{"id": DEVICE.node_id, "features": {
                controls.FEATURE: {attribute: {"targetValue": True}}}}]})
            self.assertNotIn("x-api-key", kwargs["headers"])
            self.assertTrue(kwargs["ssl"])
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["headers"]["Accept"], "application/vnd.alertme.zoo-6.5.0+json")

    async def test_disabled_has_no_reads_or_writes(self):
        control, client, session, _ = self.client(options={})
        with self.assertRaises(controls.HiveEVControlError):
            await control.async_command(DEVICE, "charge_now")
        client._get.assert_not_called()
        client.async_devices.assert_not_called()
        session.put.assert_not_called()

    async def test_fresh_guard_changed_to_charging_prevents_write(self):
        control, client, session, _ = self.client()
        client._get.return_value = {"nodes": [node("end_session")]}
        with self.assertRaises(controls.HiveEVControlError):
            await control.async_command(DEVICE, "charge_now")
        session.put.assert_not_called()

    async def test_all_http_failures_latch_disable_without_retry(self):
        for status in (302, 400, 401, 403, 404, 429, 500, 503):
            control, client, session, disable = self.client(response=Response(status))
            with self.assertRaises(controls.HiveEVControlError) as error:
                await control.async_command(DEVICE, "charge_now")
            self.assertNotIn("invented", str(error.exception))
            disable.assert_called_once()
            with patch.object(controls.time, "monotonic", return_value=1e12):
                with self.assertRaises(controls.HiveEVControlError):
                    await control.async_command(DEVICE, "charge_now")
            session.put.assert_called_once()

    async def test_timeout_and_cancellation_latch_before_any_retry(self):
        for failure in (asyncio.TimeoutError("private-response"), asyncio.CancelledError()):
            control, _, session, disable = self.client()
            session.put.side_effect = failure
            with self.assertRaises((controls.HiveEVControlError, asyncio.CancelledError)):
                await control.async_command(DEVICE, "charge_now")
            disable.assert_called_once()
            self.assertTrue(control._blocked)
            session.put.assert_called_once()

    async def test_per_device_lock_and_cooldown_prevent_double_press(self):
        control, client, session, _ = self.client()
        result = await asyncio.gather(control.async_command(DEVICE, "charge_now"),
                                      control.async_command(DEVICE, "charge_now"), return_exceptions=True)
        self.assertEqual(sum(isinstance(value, controls.HiveEVControlError) for value in result), 1)
        session.put.assert_called_once()

    async def test_multiple_devices_and_unknown_action_never_write(self):
        control, client, session, _ = self.client()
        client.async_devices.return_value = {"a": DEVICE, "b": DEVICE}
        with self.assertRaises(controls.HiveEVControlError):
            await control.async_command(DEVICE, "charge_now")
        session.put.assert_not_called()

    async def test_options_defaults_off_and_requires_owner_alfen(self):
        flow = flow_module.HiveEVOptionsFlow()
        flow.config_entry = SimpleNamespace(runtime_data=SimpleNamespace(data={"one": DEVICE}))
        result = await flow.async_step_init()
        self.assertEqual(result["data_schema"]({}), {"enable_experimental_controls": False, "owner_confirmed_alfen": False, "remove_cost_helper": False})
        rejected = await flow.async_step_init({"enable_experimental_controls": True, "owner_confirmed_alfen": False})
        self.assertIn("base", rejected["errors"])
        accepted = await flow.async_step_init(dict(OPTIONS))
        self.assertEqual(accepted["type"], "entry")

    async def test_live_opt_out_during_preflight_prevents_write(self):
        control, client, session, _ = self.client()
        options = dict(OPTIONS)
        control._options = lambda: options
        async def disable_during_read(*args, **kwargs):
            options["enable_experimental_controls"] = False
            return {"nodes": [node()]}
        client._get.side_effect = disable_during_read
        with self.assertRaises(controls.HiveEVControlError):
            await control.async_command(DEVICE, "charge_now")
        session.put.assert_not_called()

    async def test_waiter_cannot_bypass_uncertainty_latch_after_cooldown(self):
        control, client, session, disable = self.client(response=Response(503))
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed_read(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"nodes": [node()]}
        client._get.side_effect = delayed_read
        first = asyncio.create_task(control.async_command(DEVICE, "charge_now"))
        await entered.wait()
        second = asyncio.create_task(control.async_command(DEVICE, "charge_now"))
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        self.assertTrue(all(isinstance(result, controls.HiveEVControlError) for result in results))
        session.put.assert_called_once()
        client._get.assert_awaited_once()
        disable.assert_called_once()

    async def test_one_attempt_each_action_per_runtime_even_after_cooldown(self):
        control, client, session, _ = self.client()
        await control.async_command(DEVICE, "charge_now")
        with patch.object(controls.time, "monotonic", return_value=1e12):
            with self.assertRaises(controls.HiveEVControlError):
                await control.async_command(DEVICE, "charge_now")
            client._get.return_value = {"nodes": [node("end_session")]}
            await control.async_command(DEVICE, "end_session")
        self.assertEqual(session.put.call_count, 2)
        self.assertEqual(control._attempted_actions, {"charge_now", "end_session"})
