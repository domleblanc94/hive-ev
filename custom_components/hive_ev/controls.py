"""Experimental commands, never used by monitoring or polling."""
from __future__ import annotations

import asyncio
import time
from urllib.parse import quote

import aiohttp

from .api import HiveEVClient, HiveEVError, HiveEVResponseError, _number
from .const import EVSE_TYPE, NODE_ACCEPT

FEATURE = "ev_supply_equipment_v1"
WRITE_BASE = "https://api-prod.bgchprod.info/omnia/nodes/"
START_STATES = frozenset(("SCHEDULED", "PAUSED", "WAITING_TO_START", "WAITING_TO_RESUME"))
CONTROL_OPTIONS = ("enable_experimental_controls", "owner_confirmed_alfen")


def controls_enabled(options) -> bool:
    return all(options.get(key) is True for key in CONTROL_OPTIONS)


class HiveEVControlError(HiveEVError):
    """A fixed safe message; delivery or physical outcome may be unknown."""


def _value(feature, key):
    wrapper = feature.get(key)
    if not isinstance(wrapper, dict) or "reportedValue" not in wrapper:
        raise HiveEVControlError("Required reported control state is missing. Check Hive.")
    value = wrapper["reportedValue"]
    target = wrapper.get("targetValue")
    if target is not None and (type(target) is not type(value) or target != value):
        raise HiveEVControlError("Hive has a pending or contradictory state. Check Hive before another command.")
    property_status = wrapper.get("propertyStatus")
    if property_status is not None and not isinstance(property_status, str):
        raise HiveEVControlError("Hive returned invalid control state. Check Hive.")
    if isinstance(property_status, str) and property_status.upper() == "PENDING":
        raise HiveEVControlError("Hive has a pending state. Check Hive before another command.")
    return value


def check_guard(node, action):
    if node.get("nodeType") != EVSE_TYPE:
        raise HiveEVControlError("Only the confirmed Alfen EVSE is supported by these beta controls.")
    features = node.get("features")
    feature = features.get(FEATURE) if isinstance(features, dict) else None
    if not isinstance(feature, dict):
        raise HiveEVControlError("Hive EVSE control state is missing.")
    if "cableUnlock" in feature:
        unlock = _value(feature, "cableUnlock")
        if unlock is not False:
            raise HiveEVControlError("A cable unlock/end state is present or pending. Check Hive before another command.")
    state = _value(feature, "displayState")
    mode = _value(feature, "scheduleMode")
    active = _value(feature, "transactionActive")
    override = _value(feature, "transactionOverridden")
    power = _number(_value(feature, "transactionActivePowerImportW"))
    if not isinstance(state, str) or not isinstance(mode, str):
        raise HiveEVControlError("Hive returned invalid control state. Check Hive.")
    if active is not True or mode not in ("CUSTOM", "TARIFF") or power is None:
        raise HiveEVControlError("A confirmed active normal scheduled session and measured power are required. DSR is unsupported.")
    if action == "charge_now":
        if state not in START_STATES or override is not False or power != 0:
            raise HiveEVControlError("Charge now requires a settled scheduled session, no override, and reported zero power.")
    elif action == "end_session":
        if state != "CHARGING" or override is not True or power <= 0:
            raise HiveEVControlError("End charging session requires Charging, an active override, and reported positive power.")
    else:
        raise HiveEVControlError("Unsupported experimental command.")


class HiveEVControlClient:
    """One fresh preflight and at most one PUT per explicit button press."""

    def __init__(self, client: HiveEVClient, options, on_uncertain=None) -> None:
        self.client = client
        self._options = options
        self._locks = {}
        self._attempted_at = {}
        self._attempted_actions = set()
        self._blocked = False
        self._on_uncertain = on_uncertain

    @property
    def options(self):
        return self._options() if callable(self._options) else self._options

    def _block_uncertain(self):
        self._blocked = True
        if self._on_uncertain is not None:
            self._on_uncertain()

    def invalidate(self):
        """Prevent an old runtime resuming a preflight after unload or opt-out."""
        self._blocked = True

    async def async_command(self, device, action):
        if action not in ("charge_now", "end_session"):
            raise HiveEVControlError("Unsupported experimental command.")
        if self._blocked or not controls_enabled(self.options):
            raise HiveEVControlError("Experimental controls are disabled.")
        node_id, home_id = device.node_id, device.home_id
        if not all(isinstance(value, str) and 0 < len(value) <= 256 for value in (node_id, home_id)):
            raise HiveEVControlError("Charger identity is invalid.")
        async with self._locks.setdefault(node_id, asyncio.Lock()):
            if self._blocked or not controls_enabled(self.options):
                raise HiveEVControlError("Experimental controls are disabled.")
            if action in self._attempted_actions:
                raise HiveEVControlError("This action was already attempted in this trial. Check Hive before explicitly starting another trial.")
            if time.monotonic() - self._attempted_at.get(node_id, -1e9) < 60:
                raise HiveEVControlError("A command was recently attempted. Check Hive and wait at least 60 seconds; do not repeat an uncertain command.")
            devices = await self.client.async_devices()
            if len(devices) != 1 or node_id not in devices or devices[node_id].home_id != home_id:
                raise HiveEVControlError("Exactly one matching charger must be discovered before an experimental command.")
            # This authenticated GET renews the ordinary session before the write.
            payload = await self.client._get("omnia/nodes?homeId=" + quote(home_id, safe=""), nodes=True)
            if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
                raise HiveEVResponseError("Hive control preflight representation changed")
            matches = [node for node in payload["nodes"] if isinstance(node, dict) and node.get("id") == node_id]
            if len(matches) != 1:
                raise HiveEVControlError("The selected charger could not be uniquely verified.")
            check_guard(matches[0], action)
            if self._blocked or not controls_enabled(self.options):
                raise HiveEVControlError("Experimental controls are disabled.")
            attribute = "transactionOverridden" if action == "charge_now" else "cableUnlock"
            body = {"nodes": [{"id": node_id, "features": {FEATURE: {attribute: {"targetValue": True}}}}]}
            headers = {"Authorization": "Bearer " + self.client._tokens["id_token"],
                       "Accept": NODE_ACCEPT, "Content-Type": "application/json",
                       "X-AlertMe-Client": "Honeycomb React Native App",
                       "User-Agent": "HomeAssistant-HiveEV/0.2.0b3"}
            url = WRITE_BASE + quote(node_id, safe="") + "?homeId=" + quote(home_id, safe="")
            # Consume before entering transport: even timeout/cancellation may follow delivery.
            self._attempted_actions.add(action)
            self._attempted_at[node_id] = time.monotonic()
            try:
                async with self.client._session.put(url, headers=headers, json=body,
                    timeout=aiohttp.ClientTimeout(total=15), ssl=True, allow_redirects=False) as response:
                    if not 200 <= response.status < 300:
                        raise HiveEVControlError("Hive did not acknowledge the command. Delivery or outcome is uncertain; check Hive before any further action.")
            except HiveEVControlError:
                self._block_uncertain()
                raise
            except asyncio.CancelledError:
                self._block_uncertain()
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError):
                self._block_uncertain()
                raise HiveEVControlError("Command delivery is uncertain. Check Hive before any further action; do not retry automatically.") from None
            return "Hive acknowledged the request. Physical charging and the final session state are unconfirmed; check Hive and the car."
