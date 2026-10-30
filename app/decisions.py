"""Canonical local decision scopes; these attestations do not establish roles."""

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json


def decimal_value(value):
    if isinstance(value, (bool, float)) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Dezimalwerte als Zeichenkette oder ganze Zahl angeben")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Ungültiger Dezimalwert") from exc
    if not number.is_finite():
        raise ValueError("Ungültiger Dezimalwert")
    return number


def normalize(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, Decimal):
        return str(decimal_value(value))
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return {k: normalize(v) for k, v in value.items()}
    raise ValueError("Entscheidungsumfang enthält einen ungültigen Typ")


def digest(value):
    encoded = json.dumps(
        normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def scope_approval(scope, attestation):
    scope_hash = digest(scope)
    valid = (
        isinstance(attestation, dict)
        and isinstance(attestation.get("by"), str)
        and bool(attestation["by"].strip())
        and attestation.get("scope_hash") == scope_hash
    )
    return scope_hash, valid


def validity(payload):
    values = [payload.get(k) for k in ("valid_from", "valid_to", "as_of")]
    if any(not isinstance(x, str) or not x for x in values):
        raise ValueError("Gültigkeitszeitraum und Stichtag erforderlich")
    start, end, current = map(date.fromisoformat, values)
    if end < start:
        raise ValueError("Ungültiger Gültigkeitszeitraum")
    return start <= current <= end
