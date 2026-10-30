"""Read-only Hive EV transport and reported-value parsing."""
from __future__ import annotations

import asyncio
import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import time
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import APP_KEY, BASE_URL, CHARGER_TYPE, EVSE_TYPE, NODE_ACCEPT, STATUSES


class HiveEVError(Exception):
    """A sanitized error safe for Home Assistant logs."""


class HiveEVAuthError(HiveEVError):
    """Sign-in must be renewed interactively."""


class HiveEVConnectionError(HiveEVError):
    """Hive could not be reached, or throttled the request."""


class HiveEVResponseError(HiveEVError):
    """Hive returned an unexpected representation."""


@dataclass(frozen=True)
class HiveEVDevice:
    """Only the reported monitoring fields, without raw node data."""

    node_id: str = field(repr=False)
    home_id: str = field(repr=False)
    name: str
    status: str | None
    transaction_active: bool | None
    power_w: float | None
    session_energy_wh: float | None
    session_duration_s: float | None
    last_updated: datetime


def token_claims(token: str) -> dict[str, Any]:
    """Decode metadata of a token obtained from verified Cognito transport."""
    try:
        encoded = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not isinstance(claims, dict):
            raise ValueError
        return claims
    except (ValueError, IndexError, TypeError):
        raise HiveEVAuthError("Hive sign-in token is invalid") from None


def tokens_from_result(result: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep only tokens needed for renewal; never the account password."""
    previous = previous or {}
    try:
        auth = result["AuthenticationResult"]
        token = auth["IdToken"]
        refresh_token = auth.get("RefreshToken", previous.get("refresh_token"))
        expires_in = auth["ExpiresIn"]
        if not isinstance(token, str) or not token or not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError
        if type(expires_in) is not int or not 0 < expires_in <= 86400:
            raise ValueError
        claims = token_claims(token)
        user_id = claims["cognito:username"]
        if not isinstance(user_id, str) or not 0 < len(user_id) <= 256:
            raise ValueError
        expiration = claims["exp"]
        if type(expiration) not in (int, float) or not 0 < expiration <= 1e12 or not math.isfinite(expiration):
            raise ValueError
        expires_at = min(time.time() + expires_in, expiration)
        if expires_at <= time.time():
            raise ValueError
        return {"id_token": token, "refresh_token": refresh_token,
                "expires_at": expires_at, "user_id": user_id,
                "device_key": previous.get("device_key")}
    except (KeyError, ValueError, TypeError):
        raise HiveEVAuthError("Hive did not return a usable sign-in") from None


def _reported(features: dict[str, Any], feature: str, attribute: str) -> Any:
    values = features.get(feature)
    if not isinstance(values, dict):
        return None
    wrapper = values.get(attribute)
    return wrapper.get("reportedValue") if isinstance(wrapper, dict) else None


def _number(value: Any) -> float | None:
    if type(value) in (float, int) and 0 <= value <= 1e12 and math.isfinite(value):
        return float(value)
    return None


def parse_devices(payload: Any, home_id: str, now: datetime) -> dict[str, HiveEVDevice]:
    """Do not substitute target values for observed physical state."""
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise HiveEVResponseError("Hive node representation changed")
    devices = {}
    for node in payload["nodes"]:
        if not isinstance(node, dict):
            raise HiveEVResponseError("Hive node representation changed")
        if node.get("nodeType") not in (EVSE_TYPE, CHARGER_TYPE):
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not 0 < len(node_id) <= 256:
            raise HiveEVResponseError("Hive charger identifier is missing")
        features = node.get("features")
        if not isinstance(features, dict):
            raise HiveEVResponseError("Hive charger reported features are missing")
        if node["nodeType"] == EVSE_TYPE:
            feature, status_key = "ev_supply_equipment_v1", "displayState"
            power_key, energy_key, duration_key = ("transactionActivePowerImportW", "transactionEnergyTotalWh", "transactionChargeTimeSeconds")
        else:
            feature, status_key = "ev_charger_v1", "status"
            # Legacy numeric units are not established by the live EVSE test.
            power_key = energy_key = duration_key = ""
        status = _reported(features, feature, status_key)
        status = status.lower() if isinstance(status, str) and status in STATUSES else None
        active = _reported(features, feature, "transactionActive")
        active = active if isinstance(active, bool) else None
        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            name = "Hive EV charger"
        devices[node_id] = HiveEVDevice(
            node_id=node_id, home_id=home_id, name=name.strip()[:100], status=status,
            transaction_active=active,
            power_w=_number(_reported(features, feature, power_key)),
            session_energy_wh=_number(_reported(features, feature, energy_key)),
            session_duration_s=_number(_reported(features, feature, duration_key)),
            last_updated=now,
        )
    return devices


class HiveEVClient:
    """One homes read and one nodes read per home, with bounded token renewal."""

    def __init__(self, session: aiohttp.ClientSession, tokens: dict[str, Any],
                 on_tokens: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._session = session
        self._tokens = dict(tokens)
        self._on_tokens = on_tokens
        self._refresh_lock = asyncio.Lock()

    @property
    def user_id(self) -> str:
        return self._tokens["user_id"]

    async def _refresh(self, force: bool = False) -> None:
        from .auth import async_refresh_tokens

        async with self._refresh_lock:
            if not force and time.time() < self._tokens["expires_at"] - 60:
                return
            result = await async_refresh_tokens(self._tokens)
            renewed = tokens_from_result(result, self._tokens)
            if renewed["user_id"] != self.user_id:
                raise HiveEVAuthError("Hive account identity changed")
            self._tokens = renewed
            if self._on_tokens is not None:
                self._on_tokens(dict(renewed))

    async def _get(self, path: str, *, nodes: bool = False) -> Any:
        await self._refresh()
        for attempt in range(2):
            headers = {"Authorization": "Bearer " + self._tokens["id_token"],
                       "x-api-key": APP_KEY, "Content-Type": "application/json",
                       "User-Agent": "HomeAssistant-HiveEV/0.1.0"}
            if nodes:
                headers.update({"Accept": NODE_ACCEPT, "X-AlertMe-Client": "Honeycomb React Native App"})
            try:
                async with self._session.get(BASE_URL + path, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20), allow_redirects=False, ssl=True) as response:
                    if response.status in (401, 403):
                        if attempt == 0 and response.status == 401:
                            retry = True
                        else:
                            raise HiveEVAuthError("Hive authorization was rejected")
                    elif response.status == 429 or response.status >= 500:
                        raise HiveEVConnectionError("Hive is temporarily unavailable")
                    elif response.status != 200:
                        raise HiveEVResponseError("Hive did not return the expected data")
                    else:
                        retry = False
                        return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                raise HiveEVConnectionError("Cannot connect to Hive") from None
            except (ValueError, UnicodeError):
                raise HiveEVResponseError("Hive returned invalid data") from None
            if retry:
                await self._refresh(force=True)
        raise HiveEVAuthError("Hive sign-in must be renewed")

    async def async_devices(self) -> dict[str, HiveEVDevice]:
        homes = await self._get("home/owner/" + quote(self.user_id, safe=""))
        if not isinstance(homes, dict) or not isinstance(homes.get("homes"), list):
            raise HiveEVResponseError("Hive home representation changed")
        entries = homes["homes"]
        if len(entries) > 10 or not all(isinstance(home, dict) and isinstance(home.get("id"), str) and 0 < len(home["id"]) <= 256 for home in entries):
            raise HiveEVResponseError("Hive home representation changed")
        devices = {}
        for home in entries:
            payload = await self._get("omnia/nodes?homeId=" + quote(home["id"], safe=""), nodes=True)
            devices.update(parse_devices(payload, home["id"], datetime.now(timezone.utc)))
        return devices
