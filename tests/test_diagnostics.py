"""Privacy and explicit-GET-only checks for the private diagnostic download."""
import asyncio
import importlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from test_hive_ev_core import PKG, api

shapes = importlib.import_module(f"{PKG}.diagnostic_shapes")
diagnostics = importlib.import_module(f"{PKG}.diagnostics")


def raw_payload():
    secret = "private-identifier-user-token-password"
    return {"account": secret, "url": "https://private.example/secret", "nodes": [
        {"id": secret, "homeId": secret, "name": secret, "nodeType": shapes.STATION_TYPE,
         "features": {"ev_device_v1": {
             "capabilities": {"reportedValue": ["DSR", "FREE_CHARGE", "SECURE_CHARGE", "PAUSE", secret,
                                                  {"id": secret}], "targetValue": [secret],
                              "writable": False, "readOnly": True, "access": "READ_ONLY",
                              "permissions": ["READ", "WRITE", secret],
                              "reportReceivedTime": "2026-11-03T12:34:56Z"},
             secret: {"reportedValue": {"id": secret, "name": secret, "url": "https://private.example/secret"}},
             "availableChargeModes": {"reportedValue": ["eco", "fast", "stop", secret]},
         }, secret: {"displayState": {"reportedValue": secret, "targetValue": secret}}}},
        {"id": secret, "nodeType": shapes.EVSE_TYPE, "name": secret, "features": {
            "ev_supply_equipment_v1": {"displayState": {"reportedValue": "CHARGING"},
                "transactionActivePowerImportW": {"reportedValue": 5825},
                "customSchedule": {"reportedValue": {"days": [secret], "time": "23:30"}}}}},
        {"nodeType": "private-unrelated-device", "features": {secret: secret}},
    ]}


class ShapeTests(unittest.TestCase):
    def test_account_values_readings_urls_and_unknown_names_never_escape(self):
        data = shapes.sanitize_payload(raw_payload())
        encoded = json.dumps(data)
        for private in ("private-identifier-user-token-password", "https://", "2026-11-03", "5825", "CHARGING", "23:30", "PAUSE", "eco", "fast", "stop"):
            self.assertNotIn(private, encoded)
        self.assertEqual(data["nodes"][0]["node_kind"], "charging_station")
        capability = data["nodes"][0]["features"][0]["attributes"][0]
        self.assertEqual(capability["technical_capability_metadata"]["known_vocabulary"],
                         ["DSR", "FREE_CHARGE", "SECURE_CHARGE"])
        self.assertTrue(capability["technical_capability_metadata"]["does_not_establish_pause_support"])
        self.assertTrue(capability["reportedValue_present"])
        self.assertTrue(capability["targetValue_present"])
        self.assertTrue(capability["metadata"]["readOnly"])
        self.assertEqual(capability["metadata"]["permissions"], ["READ", "WRITE"])
        self.assertIn("unknown_", encoded)

    def test_metadata_does_not_accept_lookalike_flags_or_arbitrary_access(self):
        self.assertEqual(shapes.metadata({"writable": "true", "readOnly": 1,
            "access": "private-user", "permissions": ["private-token", 123]}), {})
        self.assertEqual(shapes.capability_metadata({"reportedValue": "DSR"}), {})
        self.assertEqual(shapes.metadata({"metadata": {"writable": True, "access": "READ_WRITE", "private": "secret"}}),
            {"nested_metadata": {"writable": True, "access": "READ_WRITE"}})

    def test_shapes_never_descend_into_nested_object_keys_or_values(self):
        self.assertEqual(shapes.shape({"private-key": {"private-key": "private-value"}}),
            {"type": "object", "size_bucket": "1-10", "sample_type_counts": {"object": 1}, "sample_truncated": False})

    def test_node_feature_attribute_output_and_scan_limits(self):
        node = {"nodeType": shapes.EVSE_TYPE, "features": {str(index): {
            str(attribute): {"reportedValue": ["private"] * 1000} for attribute in range(100)} for index in range(100)}}
        result = shapes.sanitize_payload({"nodes": [node] * 100})
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(json.dumps(result).encode()), shapes.MAX_BYTES)
        self.assertLessEqual(len(result["nodes"]), shapes.MAX_NODES)
        for item in result["nodes"]:
            self.assertLessEqual(len(item["features"]), shapes.MAX_FEATURES)
            for feature in item["features"]:
                self.assertLessEqual(len(feature["attributes"]), shapes.MAX_ATTRIBUTES)
        no_match = shapes.sanitize_payload({"nodes": [{}] * 1000})
        self.assertTrue(no_match["truncated"])
        self.assertEqual(no_match["nodes"], [])

    def test_primitive_unknown_and_malformed_inputs_do_not_echo_values(self):
        for value in (None, [], {"nodes": None}):
            with self.assertRaises(ValueError):
                shapes.sanitize_payload(value)
        self.assertEqual(shapes.key_label(123, frozenset()), "unknown_key_type")
        data = shapes.sanitize_payload({"nodes": [None, {"nodeType": [], "features": {}},
            {"nodeType": shapes.EVSE_TYPE, "features": "private-value"}]})
        self.assertNotIn("private-value", json.dumps(data))


class DownloadTests(unittest.IsolatedAsyncioTestCase):
    def entry(self):
        client = SimpleNamespace(_get=AsyncMock(return_value=raw_payload()),
            async_command=AsyncMock(side_effect=AssertionError("No commands allowed")),
            _session=SimpleNamespace(put=Mock(side_effect=AssertionError("No PUT allowed")),
                                     post=Mock(side_effect=AssertionError("No POST allowed"))))
        controls = SimpleNamespace(async_command=AsyncMock(side_effect=AssertionError("No commands allowed")))
        coordinator = SimpleNamespace(data={"private-node": SimpleNamespace(home_id="private/home")}, client=client, controls=controls)
        entry = SimpleNamespace(runtime_data=coordinator, data={"password": "private-password"},
                                options={"private": "private-options"})
        return entry, client, controls

    async def test_explicit_download_only_proven_get_and_never_commands(self):
        entry, client, controls = self.entry()
        client._get.assert_not_awaited()
        result = await diagnostics.async_get_config_entry_diagnostics(None, entry)
        client._get.assert_awaited_once_with("omnia/nodes?homeId=private%2Fhome", nodes=True)
        self.assertEqual(result["pause_support"], "not_determined")
        self.assertNotIn("private", json.dumps(result))
        client._session.put.assert_not_called()
        client._session.post.assert_not_called()
        client.async_command.assert_not_awaited()
        controls.async_command.assert_not_awaited()

    async def test_home_deduplication_and_bounds_no_unbounded_reads(self):
        entry, client, _ = self.entry()
        entry.runtime_data.data["second"] = SimpleNamespace(home_id="private/home")
        await diagnostics.async_get_config_entry_diagnostics(None, entry)
        self.assertEqual(client._get.await_count, 1)
        entry.runtime_data.data = {str(index): SimpleNamespace(home_id=str(index)) for index in range(11)}
        client._get.reset_mock()
        result = await diagnostics.async_get_config_entry_diagnostics(None, entry)
        self.assertEqual(result["error"], "diagnostic_home_limit")
        client._get.assert_not_awaited()

    async def test_safe_errors_never_include_dependency_messages(self):
        for failure in (api.HiveEVAuthError("private-token"), api.HiveEVConnectionError("private-url"),
                        RuntimeError("private-password"), asyncio.TimeoutError("private-account")):
            entry, client, _ = self.entry()
            client._get.side_effect = failure
            result = await diagnostics.async_get_config_entry_diagnostics(None, entry)
            self.assertEqual(result["error"], "capability_shapes_unavailable")
            self.assertNotIn("private", json.dumps(result))

    async def test_no_runtime_no_data_and_cancellation(self):
        result = await diagnostics.async_get_config_entry_diagnostics(None, SimpleNamespace())
        self.assertEqual(result["error"], "monitoring_unavailable")
        entry, client, _ = self.entry()
        entry.runtime_data.data = {}
        result = await diagnostics.async_get_config_entry_diagnostics(None, entry)
        self.assertEqual(result["error"], "no_monitored_chargers")
        entry, client, _ = self.entry()
        client._get.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await diagnostics.async_get_config_entry_diagnostics(None, entry)
