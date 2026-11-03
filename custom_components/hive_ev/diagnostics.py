"""Explicit download only: sanitized capability shapes using ordinary GETs."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import quote

from .api import HiveEVError
from .diagnostic_shapes import sanitize_payload


async def async_get_config_entry_diagnostics(hass, entry):
    """Never serialize entry data/options or change charging state."""
    result = {"diagnostic_schema": 1, "scope": "EV_technical_shapes_only",
              "pause_support": "not_determined", "does_not_establish_command_support": True,
              "home_shapes": []}
    coordinator = getattr(entry, "runtime_data", None)
    devices = getattr(coordinator, "data", None)
    client = getattr(coordinator, "client", None)
    if not isinstance(devices, dict) or client is None:
        return {**result, "error": "monitoring_unavailable"}
    if len(devices) > 64:
        return {**result, "error": "diagnostic_device_limit"}
    homes = []
    for device in devices.values():
        home_id = getattr(device, "home_id", None)
        if not isinstance(home_id, str) or not 0 < len(home_id) <= 256:
            return {**result, "error": "monitoring_representation_changed"}
        if home_id not in homes:
            homes.append(home_id)
            if len(homes) > 10:
                return {**result, "error": "diagnostic_home_limit"}
    if not homes:
        return {**result, "error": "no_monitored_chargers"}
    raw = None
    try:
        for home_id in homes:
            raw = await client._get("omnia/nodes?homeId=" + quote(home_id, safe=""), nodes=True)
            result["home_shapes"].append(sanitize_payload(raw))
            raw = None
            if len(json.dumps(result).encode("utf-8")) > 131072:
                result["home_shapes"].pop()
                result["truncated"] = True
                break
    except asyncio.CancelledError:
        raise
    except (HiveEVError, ValueError, TypeError, AttributeError, KeyError):
        return {**result, "error": "capability_shapes_unavailable"}
    except Exception:
        # A diagnostic download must not expose dependency exception messages.
        return {**result, "error": "capability_shapes_unavailable"}
    finally:
        raw = None
    return result
