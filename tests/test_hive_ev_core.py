"""Offline protocol/auth tests; HA flow/coordinator use minimal Windows stubs."""
import asyncio
import base64
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).parents[1] / "custom_components" / "hive_ev"
PKG = "hive_ev_core_test"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package
api = importlib.import_module(f"{PKG}.api")
auth = importlib.import_module(f"{PKG}.auth")
const = importlib.import_module(f"{PKG}.const")


def id_token(user="test-user", expiry=None):
    claims = {"cognito:username": user, "exp": expiry or time.time() + 3600}
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "header." + body + ".signature"


def tokens():
    return {"id_token": id_token(), "refresh_token": "private-refresh",
            "expires_at": time.time() + 3600, "user_id": "test-user", "device_key": "private-device"}


class Response:
    def __init__(self, status, data=None):
        self.status = status
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self, **kwargs):
        return self.data


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def node_payload():
    return {"nodes": [{"id": "test-evse", "name": "Charger", "nodeType": const.EVSE_TYPE,
        "features": {"ev_supply_equipment_v1": {
            "displayState": {"reportedValue": "AVAILABLE", "targetValue": "CHARGING"},
            "transactionActive": {"reportedValue": False, "targetValue": True},
            "transactionActivePowerImportW": {"targetValue": 7200},
        }}}]}


class ParserTests(unittest.TestCase):
    def test_reported_only_and_optional_unknown(self):
        devices = api.parse_devices(node_payload(), "test-home", datetime.now(timezone.utc))
        device = devices["test-evse"]
        self.assertEqual(device.status, "available")
        self.assertIs(device.transaction_active, False)
        self.assertIsNone(device.power_w)
        self.assertIsNone(device.session_energy_wh)
        self.assertNotIn("test-evse", repr(device))

    def test_bad_payload_fails_and_bad_numeric_is_unknown(self):
        with self.assertRaises(api.HiveEVResponseError):
            api.parse_devices({"nodes": [{"id": "x", "nodeType": const.EVSE_TYPE}]}, "h", datetime.now(timezone.utc))
        for bad in (True, float("nan"), float("inf"), -1, 10**1000, "private-value"):
            self.assertIsNone(api._number(bad))

    def test_token_rotation_retains_grant_and_clamps_real_expiry(self):
        expiry = time.time() + 1200
        result = {"AuthenticationResult": {"IdToken": id_token(expiry=expiry), "ExpiresIn": 3600}}
        renewed = api.tokens_from_result(result, tokens())
        self.assertEqual(renewed["refresh_token"], "private-refresh")
        self.assertEqual(renewed["device_key"], "private-device")
        self.assertEqual(renewed["expires_at"], expiry)
        self.assertNotIn("password", renewed)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_exact_get_paths_and_headers(self):
        session = Session([Response(200, {"homes": [{"id": "test-home"}]}), Response(200, node_payload())])
        client = api.HiveEVClient(session, tokens())
        result = await client.async_devices()
        self.assertEqual(len(result), 1)
        self.assertEqual([call[0] for call in session.calls], [
            "https://hive.bgchprod.info/home/owner/test-user",
            "https://hive.bgchprod.info/omnia/nodes?homeId=test-home"])
        self.assertEqual(session.calls[1][1]["headers"]["Accept"], "application/vnd.alertme.zoo-6.5.0+json")
        for _, kwargs in session.calls:
            self.assertFalse(kwargs["allow_redirects"])
            self.assertTrue(kwargs["ssl"])

    async def test_401_refresh_once_and_persists_rotated_token(self):
        session = Session([Response(401), Response(200, {"homes": []})])
        saved = []
        result = {"AuthenticationResult": {"IdToken": id_token(), "RefreshToken": "rotated", "ExpiresIn": 3600}}
        with patch.object(auth, "async_refresh_tokens", AsyncMock(return_value=result)) as refresh:
            client = api.HiveEVClient(session, tokens(), saved.append)
            self.assertEqual(await client.async_devices(), {})
        refresh.assert_awaited_once()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["refresh_token"], "rotated")

    async def test_repeated_401_stops_without_login_or_sms(self):
        session = Session([Response(401), Response(401)])
        result = {"AuthenticationResult": {"IdToken": id_token(), "ExpiresIn": 3600}}
        with patch.object(auth, "async_refresh_tokens", AsyncMock(return_value=result)) as refresh:
            with self.assertRaises(api.HiveEVAuthError):
                await api.HiveEVClient(session, tokens()).async_devices()
        self.assertEqual(len(session.calls), 2)
        refresh.assert_awaited_once()

    async def test_redirect_and_server_failure_are_safe(self):
        for status, error_type in ((302, api.HiveEVResponseError), (403, api.HiveEVAuthError), (429, api.HiveEVConnectionError), (503, api.HiveEVConnectionError)):
            session = Session([Response(status, {"private": "private-token"})])
            with self.assertRaises(error_type) as caught:
                await api.HiveEVClient(session, tokens()).async_devices()
            self.assertNotIn("private", str(caught.exception))
            self.assertEqual(len(session.calls), 1)

    async def test_refresh_expiry_requests_reauth(self):
        old = tokens()
        old["expires_at"] = time.time() - 1
        session = Session([])
        with patch.object(auth, "async_refresh_tokens", AsyncMock(side_effect=api.HiveEVAuthError("Grant expired"))):
            with self.assertRaises(api.HiveEVAuthError):
                await api.HiveEVClient(session, old).async_devices()
        self.assertEqual(session.calls, [])


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_auth_bootstrap_and_no_param_logging(self):
        login = auth._PrivateAuth("private-email", "private-password")
        self.assertEqual(login.api.getLoginInfo()["UPID"], const.COGNITO_POOL_ID)
        with self.assertNoLogs("apyhiveapi.api.hive_auth_async", level="DEBUG"):
            params = await login.get_auth_params()
        self.assertEqual(params["USERNAME"], "private-email")

    async def test_refresh_uses_saved_grant_and_device_key_only(self):
        client = SimpleNamespace(initiate_auth=Mock(return_value={"AuthenticationResult": {}}))
        fake = SimpleNamespace(async_init=AsyncMock(), async_close=AsyncMock(), client=client)
        with patch.object(auth, "_PrivateAuth", return_value=fake) as factory:
            await auth.async_refresh_tokens(tokens())
        factory.assert_called_once_with("", "")
        self.assertEqual(client.initiate_auth.call_args.kwargs["AuthFlow"], "REFRESH_TOKEN_AUTH")
        self.assertEqual(client.initiate_auth.call_args.kwargs["AuthParameters"],
                         {"REFRESH_TOKEN": "private-refresh", "DEVICE_KEY": "private-device"})
        fake.async_close.assert_awaited_once()

    async def test_registration_retry_does_not_confirm_device_twice(self):
        client = SimpleNamespace(confirm_device=Mock(return_value={}),
            update_device_status=Mock(side_effect=[OSError("private-server-data"), {}]))
        fake = SimpleNamespace(client=client, async_init=AsyncMock(), async_close=AsyncMock(),
                               generate_hash_device=AsyncMock(return_value={"test": "verifier"}))
        with patch.object(auth, "_PrivateAuth", return_value=fake):
            login = auth.HiveEVLogin("private-email", "private-password")
        login._result = {"AuthenticationResult": {"IdToken": id_token(), "RefreshToken": "grant",
            "ExpiresIn": 3600, "AccessToken": "private-access", "NewDeviceMetadata": {
                "DeviceGroupKey": "test-group", "DeviceKey": "test-device"}}}
        with self.assertRaises(api.HiveEVConnectionError) as caught:
            await login.async_register()
        self.assertNotIn("private", str(caught.exception))
        result = await login.async_register()
        self.assertEqual(result["device_key"], "test-device")
        client.confirm_device.assert_called_once()
        self.assertEqual(client.update_device_status.call_count, 2)
        self.assertEqual(fake.async_close.await_count, 2)


def load_ha_modules():
    """Load flow/coordinator against real probatio, minimal HA shell only."""
    modules = {}
    def module(name, **attrs):
        obj = ModuleType(name)
        obj.__dict__.update(attrs)
        modules[name] = obj
        return obj

    class Flow:
        source = "user"
        def __init_subclass__(cls, **kwargs):
            pass
        async def async_set_unique_id(self, value):
            self.unique_id = value
        def _abort_if_unique_id_configured(self):
            pass
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}
        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}
        def async_create_entry(self, **kwargs):
            return {"type": "entry", **kwargs}

    class Coordinator:
        def __class_getitem__(cls, arg):
            return cls
        def __init__(self, hass, logger, **kwargs):
            self.interval = kwargs["update_interval"]

    class AuthFailed(Exception):
        pass
    class UpdateFailed(Exception):
        pass
    module("homeassistant")
    module("homeassistant.config_entries", ConfigFlow=Flow, ConfigFlowResult=dict,
           ConfigEntry=object, SOURCE_REAUTH="reauth")
    module("homeassistant.const", CONF_USERNAME="username", CONF_PASSWORD="password")
    module("homeassistant.core", HomeAssistant=object)
    module("homeassistant.exceptions", ConfigEntryAuthFailed=AuthFailed)
    module("homeassistant.helpers")
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=Coordinator, UpdateFailed=UpdateFailed)
    with patch.dict(sys.modules, modules):
        flow = importlib.import_module(f"{PKG}.config_flow")
        coordinator = importlib.import_module(f"{PKG}.coordinator")
    return flow, coordinator, AuthFailed, UpdateFailed


flow_module, coordinator_module, AuthFailed, UpdateFailed = load_ha_modules()


class FlowAndCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_registration_requires_explicit_confirmation(self):
        login = SimpleNamespace(async_start=AsyncMock(), requires_sms=False,
            requires_registration=True, tokens=tokens(), clear_password=Mock(),
            async_register=AsyncMock(return_value=tokens()))
        client = SimpleNamespace(async_devices=AsyncMock(return_value={"node": object()}))
        flow = flow_module.HiveEVConfigFlow()
        flow.hass = object()
        with patch.object(flow_module, "HiveEVLogin", return_value=login), \
             patch.object(flow_module, "HiveEVClient", return_value=client):
            form = await flow.async_step_user({"username": "private-email", "password": "private-password"})
            self.assertEqual(form["step_id"], "remember")
            self.assertEqual(form["data_schema"]({"remember_device": False}), {"remember_device": False})
            login.async_register.assert_not_awaited()
            refused = await flow.async_step_remember({"remember_device": False})
            self.assertEqual(refused["errors"]["base"], "remember_required")
            login.async_register.assert_not_awaited()
            result = await flow.async_step_remember({"remember_device": True})
        login.async_register.assert_awaited_once()
        self.assertEqual(result["type"], "entry")
        self.assertEqual(set(result["data"]), {"tokens"})
        self.assertNotIn("private-password", json.dumps(result))
        login.clear_password.assert_called()

    async def test_sms_success_then_transient_read_retry_keeps_login(self):
        login = SimpleNamespace(async_start=AsyncMock(), requires_sms=True,
            requires_registration=False, tokens=tokens(), clear_password=Mock())
        async def sms(code):
            login.requires_sms = False
        login.async_sms = AsyncMock(side_effect=sms)
        client = SimpleNamespace(async_devices=AsyncMock(side_effect=[
            api.HiveEVConnectionError("temporary"), {"node": object()}]))
        flow = flow_module.HiveEVConfigFlow()
        flow.hass = object()
        with patch.object(flow_module, "HiveEVLogin", return_value=login), \
             patch.object(flow_module, "HiveEVClient", return_value=client):
            form = await flow.async_step_user({"username": "private-email", "password": "private-password"})
            self.assertEqual(form["step_id"], "sms")
            retry_form = await flow.async_step_sms({"code": "123456"})
            self.assertEqual(retry_form["errors"]["base"], "cannot_connect")
            result = await flow.async_step_sms({"code": "123456"})
        self.assertEqual(result["type"], "entry")
        login.async_sms.assert_awaited_once()

    async def test_coordinator_failure_maps_to_unavailable_or_reauth(self):
        client = SimpleNamespace(async_devices=AsyncMock(side_effect=api.HiveEVConnectionError("temporary")))
        coordinator = coordinator_module.HiveEVCoordinator(object(), object(), client)
        self.assertEqual(coordinator.interval.total_seconds(), 60)
        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
        client.async_devices.side_effect = api.HiveEVAuthError("expired")
        with self.assertRaises(AuthFailed):
            await coordinator._async_update_data()


if __name__ == "__main__":
    unittest.main()
