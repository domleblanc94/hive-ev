"""Release runtime checks using actual HA; invented HTTP responses only."""

import asyncio
from datetime import timedelta
import os
import json
from types import SimpleNamespace
from pathlib import Path
import shutil
import time

import pytest
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import MockConfigEntry, async_mock_restore_state_shutdown_restart
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.persistent_notification.helpers import (
    _async_get_or_create_notifications,
)
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMockResponse
from homeassistant.helpers import entity_registry as er

DOMAIN = "hive_ev"
SOURCE_ROOT = Path(os.environ.get("HIVE_EV_SOURCE_DIR", Path.cwd().parent / "hive-ev")).resolve()


@pytest.fixture
def custom_integrations_enabled() -> bool:
    """Allow the temporary copied custom component."""
    return True


@pytest.fixture
def hass_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Never install into the owner's actual HA or modify the Core tree."""
    target = tmp_path / "custom_components/hive_ev"
    shutil.copytree(SOURCE_ROOT / "custom_components/hive_ev", target)
    monkeypatch.syspath_prepend(str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def prototype_entry() -> MockConfigEntry:
    """An invented pre-authenticated account; never use live credentials."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="runtime-account",
        data={
            "tokens": {
                "id_token": "invented-runtime-token",
                "refresh_token": "invented-refresh",
                "expires_at": time.time() + 3600,
                "user_id": "runtime-account",
                "device_key": None,
            }
        },
    )


@pytest.fixture
def prototype_nodes() -> dict:
    """Reported Scheduled/active session, preserving known native start guard."""
    return {
        "nodes": [
            {
                "id": "runtime-evse",
                "name": "Runtime charger",
                "nodeType": "http://alertme.com/schema/json/node.class.evse.json#",
                "features": {
                    "ev_supply_equipment_v1": {
                        "displayState": {"reportedValue": "SCHEDULED"},
                        "transactionActive": {"reportedValue": True},
                        "transactionActivePowerImportW": {"reportedValue": 0},
                        "scheduleMode": {"reportedValue": "TARIFF"},
                        "transactionOverridden": {"reportedValue": False},
                    }
                },
            }
        ]
    }


@pytest.fixture
def prototype_http(
    aioclient_mock: AiohttpClientMocker, prototype_nodes: dict
) -> AiohttpClientMocker:
    """Only mocked GET endpoints exist unless a test explicitly registers PUT."""
    aioclient_mock.get(
        "https://hive.bgchprod.info/home/owner/runtime-account",
        json={"homes": [{"id": "runtime-home"}]},
    )
    aioclient_mock.get(
        "https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home",
        json=prototype_nodes,
    )
    return aioclient_mock


async def load_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Run normal actual-framework setup."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_default_off_no_writes(
    hass: HomeAssistant,
    prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """Loading and a real coordinator poll create no controls or writes."""
    await load_entry(hass, prototype_entry)
    assert not [
        entity
        for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN and entity.domain == "button"
    ]
    await prototype_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert prototype_http.mock_calls
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


@pytest.fixture
def enabled_entry(prototype_entry: MockConfigEntry) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=prototype_entry.unique_id,
        data=prototype_entry.data,
        options={"enable_experimental_controls": True, "owner_confirmed_alfen": True},
    )


def get_button(registry: er.EntityRegistry, action: str) -> str:
    entity_id = registry.async_get_entity_id(
        "button", DOMAIN, f"runtime-evse_experimental_{action}"
    )
    assert entity_id is not None
    return entity_id


def set_http(mock: AiohttpClientMocker, nodes: dict, side_effect=None) -> None:
    mock.clear_requests()
    mock.get(
        "https://hive.bgchprod.info/home/owner/runtime-account",
        json={"homes": [{"id": "runtime-home"}]},
    )
    mock.get(
        "https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home",
        json=nodes,
        side_effect=side_effect,
    )


async def press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )


async def test_options_enrollment_and_removal(
    hass: HomeAssistant,
    prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    await load_entry(hass, prototype_entry)
    flow = await hass.config_entries.options.async_init(prototype_entry.entry_id)
    rejected = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            "enable_experimental_controls": True,
            "owner_confirmed_alfen": False,
        },
    )
    assert rejected["errors"]["base"] == "alfen_confirmation_required"
    await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            "enable_experimental_controls": True,
            "owner_confirmed_alfen": True,
        },
    )
    await hass.async_block_till_done()
    button_id = get_button(entity_registry, "charge_now")
    assert hass.states.get(button_id) is not None
    assert hass.states.get(button_id).state != "unavailable"
    assert (
        len(
            [
                entity
                for entity in entity_registry.entities.values()
                if entity.platform == DOMAIN and entity.domain == "button"
            ]
        )
        == 2
    )
    hass.config_entries.async_update_entry(
        prototype_entry,
        options={"enable_experimental_controls": False, "owner_confirmed_alfen": False},
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get(button_id) is None
        or hass.states.get(button_id).state == "unavailable"
    )
    await press(hass, button_id)
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_acknowledged_start_is_one_put(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    await load_entry(hass, enabled_entry)
    coordinator = enabled_entry.runtime_data
    assert coordinator.controls.client is coordinator.client
    prototype_http.put(
        "https://api-prod.bgchprod.info/omnia/nodes/runtime-evse?homeId=runtime-home",
        status=200,
    )
    await press(hass, get_button(entity_registry, "charge_now"))
    puts = [call for call in prototype_http.mock_calls if call[0].upper() == "PUT"]
    assert len(puts) == 1
    assert puts[0][3]["Authorization"] == "Bearer invented-runtime-token"
    notifications = _async_get_or_create_notifications(hass)
    messages = " ".join(str(item) for item in notifications.values())
    assert "acknowledged" in messages and "unconfirmed" in messages
    with pytest.raises(HomeAssistantError):
        await press(hass, get_button(entity_registry, "charge_now"))
    assert (
        len([call for call in prototype_http.mock_calls if call[0].upper() == "PUT"])
        == 1
    )


@pytest.mark.parametrize("status", [401, 500])
async def test_write_rejection_disables_without_retry(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
    status: int,
) -> None:
    await load_entry(hass, enabled_entry)
    prototype_http.put(
        "https://api-prod.bgchprod.info/omnia/nodes/runtime-evse?homeId=runtime-home",
        status=status,
    )
    with pytest.raises(HomeAssistantError, match="uncertain"):
        await press(hass, get_button(entity_registry, "charge_now"))
    await hass.async_block_till_done()
    assert enabled_entry.options["enable_experimental_controls"] is False
    assert (
        len([call for call in prototype_http.mock_calls if call[0].upper() == "PUT"])
        == 1
    )
    assert not _async_get_or_create_notifications(hass)


async def test_fresh_state_prevents_stale_button_command(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    prototype_nodes: dict,
    entity_registry: er.EntityRegistry,
) -> None:
    await load_entry(hass, enabled_entry)
    prototype_nodes["nodes"][0]["features"]["ev_supply_equipment_v1"]["displayState"][
        "reportedValue"
    ] = "FINISHING"
    set_http(prototype_http, prototype_nodes)
    with pytest.raises(HomeAssistantError):
        await press(hass, get_button(entity_registry, "charge_now"))
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


@pytest.mark.parametrize("reenable", [False, True])
async def test_optout_during_preflight_never_writes(
    reenable: bool,
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    prototype_nodes: dict,
    entity_registry: er.EntityRegistry,
) -> None:
    await load_entry(hass, enabled_entry)
    reached, release = asyncio.Event(), asyncio.Event()

    async def suspended(method, url, data):
        reached.set()
        await release.wait()
        return AiohttpClientMockResponse("get", url, json=prototype_nodes)

    set_http(prototype_http, prototype_nodes, suspended)
    task = asyncio.create_task(press(hass, get_button(entity_registry, "charge_now")))
    await asyncio.wait_for(reached.wait(), timeout=5)
    hass.config_entries.async_update_entry(
        enabled_entry,
        options={"enable_experimental_controls": False, "owner_confirmed_alfen": False},
    )
    await asyncio.sleep(0)
    if reenable:
        hass.config_entries.async_update_entry(
            enabled_entry,
            options={
                "enable_experimental_controls": True,
                "owner_confirmed_alfen": True,
            },
        )
    release.set()
    with pytest.raises(HomeAssistantError):
        await task
    await hass.async_block_till_done()
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_token_save_does_not_reload_controls(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
) -> None:
    await load_entry(hass, enabled_entry)
    old_coordinator = enabled_entry.runtime_data
    hass.config_entries.async_update_entry(
        enabled_entry,
        data={
            "tokens": dict(enabled_entry.data["tokens"], id_token="new-invented-token")
        },
    )
    await hass.async_block_till_done()
    assert enabled_entry.runtime_data is old_coordinator
    assert old_coordinator.controls.client is old_coordinator.client
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_timeout_disables_without_retry(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    await load_entry(hass, enabled_entry)
    prototype_http.put(
        "https://api-prod.bgchprod.info/omnia/nodes/runtime-evse?homeId=runtime-home",
        exc=asyncio.TimeoutError(),
    )
    with pytest.raises(HomeAssistantError, match="uncertain"):
        await press(hass, get_button(entity_registry, "charge_now"))
    await hass.async_block_till_done()
    assert enabled_entry.options["enable_experimental_controls"] is False
    assert (
        len([call for call in prototype_http.mock_calls if call[0].upper() == "PUT"])
        == 1
    )


async def test_end_session_has_its_own_explicit_button(
    hass: HomeAssistant,
    enabled_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker,
    prototype_nodes: dict,
    entity_registry: er.EntityRegistry,
) -> None:
    features = prototype_nodes["nodes"][0]["features"]["ev_supply_equipment_v1"]
    features["displayState"]["reportedValue"] = "CHARGING"
    features["transactionOverridden"]["reportedValue"] = True
    features["transactionActivePowerImportW"]["reportedValue"] = 7100
    set_http(prototype_http, prototype_nodes)
    await load_entry(hass, enabled_entry)
    prototype_http.put(
        "https://api-prod.bgchprod.info/omnia/nodes/runtime-evse?homeId=runtime-home",
        status=200,
    )
    await press(hass, get_button(entity_registry, "end_session"))
    assert (
        len([call for call in prototype_http.mock_calls if call[0].upper() == "PUT"])
        == 1
    )
    put = [call for call in prototype_http.mock_calls if call[0].upper() == "PUT"][0]
    assert put[2] == {
        "nodes": [
            {
                "id": "runtime-evse",
                "features": {
                    "ev_supply_equipment_v1": {"cableUnlock": {"targetValue": True}}
                },
            }
        ]
    }
    await hass.async_block_till_done()
    status_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "runtime-evse_status"
    )
    assert status_id is not None
    assert hass.states.get(status_id).state == "Charging"
    buttons = [
        entity.unique_id
        for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN and entity.domain == "button"
    ]
    assert set(buttons) == {
        "runtime-evse_experimental_charge_now",
        "runtime-evse_experimental_end_session",
    }


async def test_diagnostics_privacy_get_only(hass: HomeAssistant, prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker, prototype_nodes: dict, entity_registry: er.EntityRegistry) -> None:
    await load_entry(hass, prototype_entry)
    node = prototype_nodes["nodes"][0]
    node["id"] = "private-device-id"
    node["name"] = "private-owner-name"
    node["features"]["ev_device_v1"] = {
        "capabilities": {"reportedValue": ["DSR", "FREE_CHARGE", "SECURE_CHARGE", "private-capability"], "writable": True},
        "availableChargeModes": {"reportedValue": ["private-mode", {"private-key": "https://private.invalid"}]} }
    node["features"]["private-owner@example.invalid"] = {"installerPassword": {"reportedValue": "private-password"}}
    prototype_http.clear_requests()
    prototype_http.get("https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home", json=prototype_nodes)
    integration = await async_get_integration(hass, DOMAIN)
    module = await integration.async_get_platform("diagnostics")
    result = await module.async_get_config_entry_diagnostics(hass, prototype_entry)
    assert "error" not in result
    assert result["pause_support"] == "not_determined"
    assert result["does_not_establish_command_support"] is True
    encoded = json.dumps(result)
    for secret in ("private-device-id", "private-owner-name", "private-capability", "private-mode", "private-key",
        "private-owner@example.invalid", "installerPassword", "private-password", "https://private.invalid",
        "runtime-home", "invented-runtime-token", "invented-refresh", prototype_entry.entry_id, "SCHEDULED", "TARIFF"):
        assert secret not in encoded
    assert "DSR" in encoded and "FREE_CHARGE" in encoded and "SECURE_CHARGE" in encoded
    assert len(prototype_http.mock_calls) == 1
    assert prototype_http.mock_calls[0][0].upper() == "GET"
    assert str(prototype_http.mock_calls[0][1]) == "https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home"
    assert prototype_http.mock_calls[0][3]["Accept"] == "application/vnd.alertme.zoo-6.5.0+json"
    assert not prototype_entry.options
    assert not [entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.domain == "button"]


async def test_diagnostics_error_redaction(hass: HomeAssistant, prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker, caplog: pytest.LogCaptureFixture) -> None:
    await load_entry(hass, prototype_entry)
    prototype_http.clear_requests()
    secret = "private-error-password-token-https://secret.invalid"
    prototype_http.get("https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home", exc=RuntimeError(secret))
    integration = await async_get_integration(hass, DOMAIN)
    module = await integration.async_get_platform("diagnostics")
    result = await module.async_get_config_entry_diagnostics(hass, prototype_entry)
    assert result["error"] == "capability_shapes_unavailable"
    assert secret not in json.dumps(result)
    assert secret not in caplog.text
    assert len(prototype_http.mock_calls) == 1


async def test_diagnostics_missing_runtime(hass: HomeAssistant, prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker) -> None:
    await load_entry(hass, prototype_entry)
    prototype_http.clear_requests()
    integration = await async_get_integration(hass, DOMAIN)
    module = await integration.async_get_platform("diagnostics")
    result = await module.async_get_config_entry_diagnostics(hass, MockConfigEntry(domain=DOMAIN, data={}))
    assert result["error"] == "monitoring_unavailable"
    assert not prototype_http.mock_calls


async def test_diagnostics_home_limit(hass: HomeAssistant, prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker) -> None:
    await load_entry(hass, prototype_entry)
    prototype_http.clear_requests()
    prototype_entry.runtime_data.data = {str(i): SimpleNamespace(home_id=f"bounded-home-{i}") for i in range(20)}
    integration = await async_get_integration(hass, DOMAIN)
    module = await integration.async_get_platform("diagnostics")
    result = await module.async_get_config_entry_diagnostics(hass, prototype_entry)
    assert result["error"] == "diagnostic_home_limit"
    assert "bounded-home" not in json.dumps(result)
    assert not prototype_http.mock_calls


async def test_diagnostics_cancel_propagates(hass: HomeAssistant, prototype_entry: MockConfigEntry,
    prototype_http: AiohttpClientMocker) -> None:
    await load_entry(hass, prototype_entry)
    prototype_http.clear_requests()
    prototype_http.get("https://hive.bgchprod.info/omnia/nodes?homeId=runtime-home", exc=asyncio.CancelledError())
    integration = await async_get_integration(hass, DOMAIN)
    module = await integration.async_get_platform("diagnostics")
    with pytest.raises(asyncio.CancelledError):
        await module.async_get_config_entry_diagnostics(hass, prototype_entry)
    assert len(prototype_http.mock_calls) == 1
    assert prototype_http.mock_calls[0][0].upper() == "GET"


async def enable_energy_helper(hass: HomeAssistant, entry: MockConfigEntry,
    registry: er.EntityRegistry) -> str:
    """Enable the registered optional entity through HA, then reload normally."""
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "runtime-evse_energy_dashboard_helper")
    assert entity_id is not None
    registry.async_update_entity(entity_id, disabled_by=None)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    return entity_id


def energy_feature(nodes: dict) -> dict:
    """Use ordinary reported telemetry, independent of session counters."""
    return nodes["nodes"][0]["features"]["ev_supply_equipment_v1"]


async def tick_refresh(hass: HomeAssistant, entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory, seconds: int) -> None:
    """Advance receipt time and perform the normal coordinator HTTP refresh."""
    freezer.tick(timedelta(seconds=seconds))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_energy_helper_optional_registry_and_metadata(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry) -> None:
    """The helper requires explicit entity enabling and exposes valid energy metadata."""
    await load_entry(hass, prototype_entry)
    helper_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "runtime-evse_energy_dashboard_helper")
    assert helper_id is not None
    registered = entity_registry.async_get(helper_id)
    assert registered is not None
    assert registered.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(helper_id) is None
    assert not prototype_entry.options
    helper_id = await enable_energy_helper(hass, prototype_entry, entity_registry)
    state = hass.states.get(helper_id)
    assert state is not None
    assert float(state.state) == 0
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["estimated"] is True and state.attributes["helper"] is True
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}
    assert not [entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.domain == "button"]


async def test_energy_helper_accumulates_across_session_reset(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry, freezer: FrozenDateTimeFactory) -> None:
    """Two observed7000W minute intervals add energy without copying resettable counters."""
    feature = energy_feature(prototype_nodes)
    feature["transactionActivePowerImportW"]["reportedValue"] = 7000
    feature["transactionEnergyTotalWh"] = {"reportedValue": 5000}
    set_http(prototype_http, prototype_nodes)
    await load_entry(hass, prototype_entry)
    helper_id = await enable_energy_helper(hass, prototype_entry, entity_registry)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(7000 / 60000, abs=1e-6)
    feature["transactionEnergyTotalWh"]["reportedValue"] = 0
    feature["transactionChargeTimeSeconds"] = {"reportedValue": 0}
    set_http(prototype_http, prototype_nodes)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(2 * 7000 / 60000, abs=1e-6)
    assert len([entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.unique_id == "runtime-evse_energy_dashboard_helper"]) == 1


async def test_energy_helper_restore_never_backfills_offline_interval(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry, freezer: FrozenDateTimeFactory) -> None:
    """HA restore storage preserves the total and starts a new baseline after downtime."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    await load_entry(hass, prototype_entry)
    helper_id = await enable_energy_helper(hass, prototype_entry, entity_registry)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    before = float(hass.states.get(helper_id).state)
    assert await hass.config_entries.async_unload(prototype_entry.entry_id)
    await async_mock_restore_state_shutdown_restart(hass)
    freezer.tick(timedelta(seconds=600))
    assert await hass.config_entries.async_setup(prototype_entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before + 7000 / 60000, abs=1e-6)
    assert len([entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.unique_id == "runtime-evse_energy_dashboard_helper"]) == 1


async def test_energy_helper_unknown_failure_and_gap_skip_energy(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry, freezer: FrozenDateTimeFactory) -> None:
    """Invalid data and failed/gapped polls do not manufacture missing energy."""
    feature = energy_feature(prototype_nodes)
    feature["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    await load_entry(hass, prototype_entry)
    helper_id = await enable_energy_helper(hass, prototype_entry, entity_registry)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    before = float(hass.states.get(helper_id).state)
    del feature["transactionActivePowerImportW"]["reportedValue"]
    set_http(prototype_http, prototype_nodes)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert hass.states.get(helper_id).state == "unavailable"
    feature["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    prototype_http.clear_requests()
    prototype_http.get("https://hive.bgchprod.info/home/owner/runtime-account", status=503)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert hass.states.get(helper_id).state == "unavailable"
    set_http(prototype_http, prototype_nodes)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, prototype_entry, freezer, 240)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before + 7000 / 60000, abs=1e-6)
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_energy_helper_late_power_has_one_disabled_candidate(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry) -> None:
    """An initially missing reading never invents a source or duplicate helper."""
    feature = energy_feature(prototype_nodes)
    del feature["transactionActivePowerImportW"]["reportedValue"]
    set_http(prototype_http, prototype_nodes)
    await load_entry(hass, prototype_entry)
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "runtime-evse_energy_dashboard_helper") is None
    feature["transactionActivePowerImportW"]["reportedValue"] = 0
    set_http(prototype_http, prototype_nodes)
    await prototype_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    await prototype_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    helper_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "runtime-evse_energy_dashboard_helper")
    assert helper_id is not None
    assert entity_registry.async_get(helper_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(helper_id) is None
    assert len([entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.unique_id == "runtime-evse_energy_dashboard_helper"]) == 1


@pytest.fixture
def cost_entry(prototype_entry: MockConfigEntry) -> MockConfigEntry:
    """An invented opt-in price source, independent of any electricity supplier."""
    return MockConfigEntry(domain=DOMAIN, unique_id=prototype_entry.unique_id,
        data=prototype_entry.data, options={"electricity_rate_sensor": "sensor.runtime_rate",
            "cost_currency": "GBP"})


def cost_entity_id(registry: er.EntityRegistry, currency: str = "GBP") -> str:
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"runtime-evse_cost_helper_{currency}")
    assert entity_id is not None
    return entity_id


async def test_cost_optional_and_selected_rate_metadata(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry) -> None:
    """No cost helper exists until the owner selects a supported current rate."""
    await load_entry(hass, prototype_entry)
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "runtime-evse_cost_helper_GBP") is None
    hass.states.async_set("sensor.runtime_rate", "15", {"unit_of_measurement": "p/kWh"})
    flow = await hass.config_entries.options.async_init(prototype_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": False, "owner_confirmed_alfen": False,
        "electricity_rate_sensor": "sensor.runtime_rate"})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert prototype_entry.options["electricity_rate_sensor"] == "sensor.runtime_rate"
    helper_id = cost_entity_id(entity_registry)
    state = hass.states.get(helper_id)
    assert state is not None
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["state_class"] == "total"
    assert state.attributes["unit_of_measurement"] == "GBP"
    assert state.attributes["estimated"] is True and state.attributes["helper"] is True
    assert not [entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.domain == "button"]
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_cost_rate_change_splits_interval(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """Changing the local rate divides an observed power interval without another API read."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "10", {"unit_of_measurement": "p/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    calls_before = len(prototype_http.mock_calls)
    freezer.tick(timedelta(seconds=30))
    hass.states.async_set("sensor.runtime_rate", "30", {"unit_of_measurement": "p/kWh"})
    await hass.async_block_till_done()
    assert len(prototype_http.mock_calls) == calls_before
    await tick_refresh(hass, cost_entry, freezer, 30)
    assert float(hass.states.get(helper_id).state) == pytest.approx(7 * (0.1 + 0.3) / 120, abs=1e-6)
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_cost_negative_credit_and_restore(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """Credits decrease a monetary TOTAL, restored without charging for downtime."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "-0.2", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    await tick_refresh(hass, cost_entry, freezer, 60)
    before = float(hass.states.get(helper_id).state)
    assert before == pytest.approx(-7 * 0.2 / 60, abs=1e-6)
    assert await hass.config_entries.async_unload(cost_entry.entry_id)
    await async_mock_restore_state_shutdown_restart(hass)
    freezer.tick(timedelta(seconds=600))
    assert await hass.config_entries.async_setup(cost_entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, cost_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(2 * before, abs=1e-6)


async def test_cost_invalid_price_never_bridges_unknown_period(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """A missing rate leaves costs unavailable and recovery starts a fresh observation."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    await tick_refresh(hass, cost_entry, freezer, 60)
    before = float(hass.states.get(helper_id).state)
    hass.states.async_set("sensor.runtime_rate", "unavailable", {"unit_of_measurement": "GBP/kWh"})
    await hass.async_block_till_done()
    assert hass.states.get(helper_id).state == "unavailable"
    await tick_refresh(hass, cost_entry, freezer, 60)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await hass.async_block_till_done()
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, cost_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before + 7 * 0.1 / 60, abs=1e-6)


async def test_cost_repeated_rate_events_do_not_refresh_stale_power(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """Local rate updates cannot extend the age of an old cloud power reading."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    cost_entry.runtime_data._unschedule_refresh()
    cost_entry.runtime_data.update_interval = None
    for price in (0.2, 0.3, 0.4):
        freezer.tick(timedelta(seconds=60))
        hass.states.async_set("sensor.runtime_rate", str(price), {"unit_of_measurement": "GBP/kWh"})
        await hass.async_block_till_done()
    previous = float(hass.states.get(helper_id).state)
    freezer.tick(timedelta(seconds=60))
    hass.states.async_set("sensor.runtime_rate", "0.5", {"unit_of_measurement": "GBP/kWh"})
    await hass.async_block_till_done()
    assert hass.states.get(helper_id).state == "unavailable"
    await cost_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert float(hass.states.get(helper_id).state) == pytest.approx(previous, abs=1e-6)


@pytest.mark.parametrize(("unit", "price", "currency", "per_kwh"), [
    ("GBp/kWh", 15, "GBP", 0.15), ("EUR/kWh", 0.2, "EUR", 0.2),
    ("USD/MWh", 120, "USD", 0.12), ("JPY/kWh", 20, "JPY", 20),
])
async def test_cost_provider_neutral_units(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory, unit: str, price: float,
    currency: str, per_kwh: float) -> None:
    """Explicit currency codes and major/minor/megawatt-hour conversions work in HA."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", str(price), {"unit_of_measurement": unit})
    await load_entry(hass, prototype_entry)
    flow = await hass.config_entries.options.async_init(prototype_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": False, "owner_confirmed_alfen": False,
        "electricity_rate_sensor": "sensor.runtime_rate"})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert prototype_entry.options["cost_currency"] == currency
    helper_id = cost_entity_id(entity_registry, currency)
    assert hass.states.get(helper_id).attributes["unit_of_measurement"] == currency
    await tick_refresh(hass, prototype_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(7 * per_kwh / 60, abs=1e-6)


async def test_cost_config_preserves_controls_and_remove_keeps_monitoring(hass: HomeAssistant,
    enabled_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    entity_registry: er.EntityRegistry) -> None:
    """Cost options retain prior enrollment, and explicit removal clears only cost settings."""
    hass.states.async_set("sensor.runtime_rate", "0.2", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, enabled_entry)
    flow = await hass.config_entries.options.async_init(enabled_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": True, "owner_confirmed_alfen": True,
        "electricity_rate_sensor": "sensor.runtime_rate"})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert enabled_entry.options["enable_experimental_controls"] is True
    assert enabled_entry.options["owner_confirmed_alfen"] is True
    helper_id = cost_entity_id(entity_registry)
    assert hass.states.get(helper_id) is not None
    assert hass.states.get(get_button(entity_registry, "charge_now")) is not None
    flow = await hass.config_entries.options.async_init(enabled_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": True, "owner_confirmed_alfen": True,
        "remove_cost_helper": True})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert "electricity_rate_sensor" not in enabled_entry.options
    assert "cost_currency" not in enabled_entry.options
    assert hass.states.get(helper_id).state == "unavailable"
    assert hass.states.get(helper_id).attributes["restored"] is True
    assert enabled_entry.runtime_data.data["runtime-evse"].power_w == 0
    assert hass.states.get(get_button(entity_registry, "charge_now")) is not None
    assert {call[0].upper() for call in prototype_http.mock_calls} == {"GET"}


async def test_cost_rejects_ambiguous_price_unit(hass: HomeAssistant,
    prototype_entry: MockConfigEntry, prototype_http: AiohttpClientMocker) -> None:
    """A dollar sign alone does not tell the integration which dollar currency to use."""
    hass.states.async_set("sensor.runtime_rate", "0.2", {"unit_of_measurement": "$/kWh"})
    await load_entry(hass, prototype_entry)
    flow = await hass.config_entries.options.async_init(prototype_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": False, "owner_confirmed_alfen": False,
        "electricity_rate_sensor": "sensor.runtime_rate"})
    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_rate_sensor"
    assert not prototype_entry.options


async def test_cost_currency_change_gets_separate_total(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """Re-enrolling a changed currency cannot relabel an existing monetary amount."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    gbp_id = cost_entity_id(entity_registry)
    await tick_refresh(hass, cost_entry, freezer, 60)
    assert float(hass.states.get(gbp_id).state) > 0
    hass.states.async_set("sensor.runtime_rate", "0.2", {"unit_of_measurement": "USD/kWh"})
    await hass.async_block_till_done()
    assert hass.states.get(gbp_id).state == "unavailable"
    flow = await hass.config_entries.options.async_init(cost_entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], user_input={
        "enable_experimental_controls": False, "owner_confirmed_alfen": False,
        "electricity_rate_sensor": "sensor.runtime_rate"})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert cost_entry.options["cost_currency"] == "USD"
    usd_id = cost_entity_id(entity_registry, "USD")
    assert usd_id != gbp_id
    assert float(hass.states.get(usd_id).state) == 0
    assert hass.states.get(usd_id).attributes["unit_of_measurement"] == "USD"


@pytest.fixture
async def mock_recorder_before_hass(async_test_recorder):
    """Apply standard HA Recorder test patches before creating hass."""


async def test_cost_recorder_sum_includes_negative_tariff_credit(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory, recorder_mock) -> None:
    """Actual Recorder stores signed cost changes for statistics-based daily display."""
    from pytest_homeassistant.components.recorder.common import (
        async_wait_recording_done, do_adhoc_statistics, get_start_time,
        statistics_during_period,
    )
    from homeassistant.util import dt as dt_util

    start = get_start_time(dt_util.utcnow())
    freezer.move_to(start)
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    await async_wait_recording_done(hass)
    await tick_refresh(hass, cost_entry, freezer, 60)
    await async_wait_recording_done(hass)
    hass.states.async_set("sensor.runtime_rate", "-0.2", {"unit_of_measurement": "GBP/kWh"})
    await hass.async_block_till_done()
    await tick_refresh(hass, cost_entry, freezer, 60)
    await tick_refresh(hass, cost_entry, freezer, 60)
    await async_wait_recording_done(hass)
    expected = 7 * (0.1 - 0.2 - 0.2) / 60
    assert float(hass.states.get(helper_id).state) == pytest.approx(expected, abs=1e-6)
    do_adhoc_statistics(hass, start=start)
    await async_wait_recording_done(hass)
    stats = statistics_during_period(hass, start, period="5minute", statistic_ids={helper_id})
    assert helper_id in stats
    assert len(stats[helper_id]) == 1
    assert stats[helper_id][0]["state"] == pytest.approx(expected, abs=1e-6)
    assert stats[helper_id][0]["sum"] == pytest.approx(expected, abs=1e-6)
    # Roll up the observed hour and query a real daily signed change statistic.
    do_adhoc_statistics(hass, start=start.replace(minute=55))
    await async_wait_recording_done(hass)
    from homeassistant.components.recorder import statistics
    daily = statistics.statistics_during_period(hass, start.replace(hour=0, minute=0),
        None, {helper_id}, "day", None, {"change", "sum"})
    assert len(daily[helper_id]) == 1
    assert daily[helper_id][0]["sum"] == pytest.approx(expected, abs=1e-6)
    assert daily[helper_id][0]["change"] == pytest.approx(expected, abs=1e-6)



async def test_cost_rate_event_cannot_bridge_long_power_gap(hass: HomeAssistant,
    cost_entry: MockConfigEntry, prototype_http: AiohttpClientMocker,
    prototype_nodes: dict, entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory) -> None:
    """A late rate event does not disguise a cloud power observation gap."""
    energy_feature(prototype_nodes)["transactionActivePowerImportW"]["reportedValue"] = 7000
    set_http(prototype_http, prototype_nodes)
    hass.states.async_set("sensor.runtime_rate", "0.1", {"unit_of_measurement": "GBP/kWh"})
    await load_entry(hass, cost_entry)
    helper_id = cost_entity_id(entity_registry)
    cost_entry.runtime_data._unschedule_refresh()
    cost_entry.runtime_data.update_interval = None
    freezer.tick(timedelta(seconds=170))
    hass.states.async_set("sensor.runtime_rate", "0.2", {"unit_of_measurement": "GBP/kWh"})
    await hass.async_block_till_done()
    before = float(hass.states.get(helper_id).state)
    assert before == pytest.approx(7 * 0.1 * 170 / 3600, abs=1e-6)
    await tick_refresh(hass, cost_entry, freezer, 130)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before, abs=1e-6)
    await tick_refresh(hass, cost_entry, freezer, 60)
    assert float(hass.states.get(helper_id).state) == pytest.approx(before + 7 * 0.2 / 60, abs=1e-6)
