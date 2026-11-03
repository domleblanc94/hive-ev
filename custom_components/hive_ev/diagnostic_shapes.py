"""Bounded EV capability shapes; no account identifiers or raw readings."""
from __future__ import annotations

from collections import Counter
import hashlib
from itertools import chain, islice
import json

from .const import CHARGER_TYPE, EVSE_TYPE

STATION_TYPE = "http://alertme.com/schema/json/node.class.charging.station.json#"
NODE_KINDS = {EVSE_TYPE: "evse", CHARGER_TYPE: "charger", STATION_TYPE: "charging_station"}
KNOWN_FEATURES = frozenset(("ev_supply_equipment_v1", "ev_charger_v1", "ev_device_v1", "ev_charging_station_v1"))
KNOWN_ATTRIBUTES = frozenset((
    "capabilities", "availableChargeModes", "chargeMode", "displayState", "status",
    "authorizationMode", "authorise", "cableUnlock", "transactionOverridden", "transactionToResume",
    "transactionActive", "transactionActivePowerImportW", "transactionEnergyTotalWh",
    "transactionChargeTimeSeconds", "scheduleMode", "transactionReadyBy",
    "customSchedule", "tariffSchedule", "tariffScheduleType",
))
FLAG_KEYS = frozenset(("writable", "readOnly", "readable", "isWritable", "isReadOnly"))
ACCESS_KEYS = frozenset(("access", "accessMode", "permission", "permissions"))
ACCESS_VALUES = frozenset(("READ", "WRITE", "READ_WRITE", "READ_ONLY", "WRITE_ONLY", "R", "W", "RW"))
CAPABILITIES = frozenset(("DSR", "FREE_CHARGE", "SECURE_CHARGE"))
MAX_NODES = 4
MAX_FEATURES = 12
MAX_ATTRIBUTES = 32
MAX_BYTES = 65536


def key_label(key, known):
    """Unknown keys are opaque hashes, never names taken from an account."""
    if isinstance(key, str) and key in known:
        return key
    if not isinstance(key, str):
        return "unknown_key_type"
    return "unknown_" + hashlib.sha256(key[:4096].encode("utf-8", errors="replace")).hexdigest()[:16]


def _type(value):
    if value is None:
        return "null"
    return {str: "string", bool: "boolean", int: "number", float: "number",
            list: "array", dict: "object"}.get(type(value), "unsupported")


def shape(value):
    """Never descend into or return reading values or nested account keys."""
    result = {"type": _type(value)}
    if isinstance(value, (list, dict)):
        length = len(value)
        result["size_bucket"] = "empty" if length == 0 else "1-10" if length <= 10 else "11-100" if length <= 100 else "over_100"
        values = value.values() if isinstance(value, dict) else value
        counts = Counter(_type(item) for item in islice(values, 64))
        result["sample_type_counts"] = dict(sorted(counts.items()))
        result["sample_truncated"] = length > 64
    return result


def _direct_metadata(value):
    if not isinstance(value, dict):
        return {}
    result = {key: value[key] for key in sorted(FLAG_KEYS) if type(value.get(key)) is bool}
    for key in sorted(ACCESS_KEYS):
        entry = value.get(key)
        # Only fixed vocabulary; arbitrary strings never pass through.
        if isinstance(entry, str) and entry in ACCESS_VALUES:
            result[key] = entry
        elif isinstance(entry, list):
            allowed = sorted({item for item in entry[:16] if isinstance(item, str) and item in ACCESS_VALUES})
            if allowed:
                result[key] = allowed
    return result


def metadata(value):
    """Recognize only direct metadata and a single explicit metadata dictionary."""
    result = _direct_metadata(value)
    if isinstance(value, dict):
        nested = _direct_metadata(value.get("metadata"))
        if nested:
            result["nested_metadata"] = nested
    return result


def capability_metadata(wrapper):
    """Shared app vocabulary is descriptive, not proof of a supported command."""
    if not isinstance(wrapper, dict):
        return {}
    value = wrapper.get("reportedValue")
    if not isinstance(value, list):
        return {}
    known = sorted({item for item in value[:64] if isinstance(item, str) and item in CAPABILITIES})
    unknown = [item for item in value[:64] if not (isinstance(item, str) and item in CAPABILITIES)]
    return {"known_vocabulary": known, "unknown_type_counts": dict(sorted(Counter(_type(item) for item in unknown).items())),
            "sample_truncated": len(value) > 64, "does_not_establish_pause_support": True}


def sanitize_payload(payload):
    """Return only EV technical field shapes, bounded independently of payload size."""
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise ValueError("Invalid diagnostic representation")
    output = {"nodes": [], "truncated": False}
    for raw_index, raw in enumerate(payload["nodes"]):
        if raw_index >= 512:
            output["truncated"] = True
            break
        if not isinstance(raw, dict):
            continue
        node_type = raw.get("nodeType")
        if not isinstance(node_type, str) or node_type not in NODE_KINDS:
            continue
        if len(output["nodes"]) >= MAX_NODES:
            output["truncated"] = True
            break
        features = raw.get("features")
        node = {"node_kind": NODE_KINDS[node_type], "features_shape": shape(features), "features": []}
        if isinstance(features, dict):
            entries = chain(((key, features[key]) for key in sorted(KNOWN_FEATURES) if key in features),
                            ((key, value) for key, value in features.items() if key not in KNOWN_FEATURES))
            for index, (feature_key, feature) in enumerate(entries):
                if index >= MAX_FEATURES:
                    output["truncated"] = True
                    break
                item = {"key": key_label(feature_key, KNOWN_FEATURES), "shape": shape(feature),
                        "metadata": metadata(feature), "attributes": []}
                if isinstance(feature, dict):
                    for attr_index, (attribute, wrapper) in enumerate(feature.items()):
                        if attr_index >= MAX_ATTRIBUTES:
                            output["truncated"] = True
                            break
                        attribute_item = {"key": key_label(attribute, KNOWN_ATTRIBUTES), "shape": shape(wrapper), "metadata": metadata(wrapper)}
                        if isinstance(wrapper, dict):
                            for reading in ("reportedValue", "targetValue"):
                                attribute_item[reading + "_present"] = reading in wrapper
                                if reading in wrapper:
                                    attribute_item[reading + "_shape"] = shape(wrapper[reading])
                            if feature_key == "ev_device_v1" and attribute == "capabilities":
                                attribute_item["technical_capability_metadata"] = capability_metadata(wrapper)
                        item["attributes"].append(attribute_item)
                node["features"].append(item)
        output["nodes"].append(node)
        if len(json.dumps(output).encode("utf-8")) > MAX_BYTES:
            output["nodes"].pop()
            output["truncated"] = True
            break
    return output
