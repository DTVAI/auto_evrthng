"""The live catalogue with canonical examples and validation schemas."""

from copy import deepcopy
from functools import lru_cache
import json
from .catalog import catalog as static_catalog
from .contracts import input_schema
from .domains import (
    communication,
    recruiting,
    personnel,
    staffing,
    orchestration,
    platform,
)

_DOMAINS = (communication, recruiting, personnel, staffing, orchestration, platform)
_LABELS = {
    "person_id": "Personenkennung",
    "application_id": "Bewerbungskennung",
    "case_id": "Vorgangskennung",
    "source": "Quelle / Beleg",
    "old": "Bisheriger Wert",
    "new": "Neuer Wert",
    "current": "Geprüfter Ausgangswert",
    "valid_from": "Gültig ab",
    "valid_to": "Gültig bis",
    "as_of": "Prüfstichtag",
    "revision": "Revision",
    "currency": "Währung",
    "basis": "Bezugsbasis",
    "people": "Personen / Positionen",
    "percentage": "Änderung in Prozent",
    "mode": "Berechnungsmodus",
    "approval": "Lokale Freigabeangaben",
    "scope_hash": "Hash des geprüften Umfangs",
    "by": "Prüfende Stelle",
    "hours": "Stunden",
    "rate": "Stundensatz",
    "amount": "Betrag",
    "invoice_lines": "Rechnungspositionen",
    "confirmed_lines": "Bestätigte Positionen",
    "template": "Vorlagentext",
    "fields": "Vorlagenfelder",
    "required_role": "Erforderliche Rolle (lokale Prüfangabe)",
    "start": "Beginn",
    "end": "Ende",
    "start_date": "Startdatum",
    "recipients": "Empfänger",
    "address": "Adresse",
    "role": "Rolle",
    "verified": "Nachweis manuell bestätigt",
    "rules": "Regeln",
    "message": "Nachricht",
    "subject": "Betreff",
    "sender": "Absender",
}


def _label_schema(schema):
    for key, child in schema.get("properties", {}).items():
        child.setdefault("title", _LABELS.get(key, key.replace("_", " ")))
        _label_schema(child)
    if isinstance(schema.get("items"), dict):
        _label_schema(schema["items"])
    for child in schema.get("anyOf", []):
        _label_schema(child)
    return schema


def _fields(value, path=""):
    rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            rows.extend(_fields(child, f"{path}.{key}" if path else key))
    elif isinstance(value, list):
        if value:
            rows.extend(_fields(value[0], path + "[]"))
        else:
            rows.append(
                {"path": path, "description": path, "example": [], "type": "array"}
            )
    else:
        kind = (
            "boolean"
            if isinstance(value, bool)
            else "integer"
            if isinstance(value, int)
            else "number"
            if isinstance(value, float)
            else "string"
            if isinstance(value, str)
            else "null"
        )
        rows.append(
            {
                "path": path,
                "description": path.replace("_", " "),
                "example": value,
                "type": kind,
            }
        )
    return rows


@lru_cache(maxsize=256)
def _sample_result(tool_id, serialized):
    module = next(x for x in _DOMAINS if tool_id in x.TOOL_IDS)
    result = module.run(tool_id, json.loads(serialized))
    return result["status"], result["summary"]


def tool_definition(tool_id):
    item = next((x for x in static_catalog() if x["id"] == tool_id), None)
    module = next((x for x in _DOMAINS if tool_id in x.TOOL_IDS), None)
    if item is None or module is None:
        raise ValueError(f"Unknown tool: {tool_id}")
    item = deepcopy(item)
    sample = deepcopy(module.SAMPLES[tool_id])
    status, summary = _sample_result(
        tool_id, json.dumps(sample, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    help_data = item.setdefault("help", {})
    descriptions = {
        field["path"]: field.get("description")
        for field in help_data.get("input_fields", [])
    }
    fields = _fields(sample)
    for field in fields:
        leaf = field["path"].replace("[]", "").split(".")[-1]
        field["description"] = descriptions.get(field["path"]) or _LABELS.get(
            leaf, field["description"]
        )
    help_data.update(
        sample_input=deepcopy(sample),
        input_fields=fields,
        sample_status=status,
        expected_status=status,
        what_it_checks=summary,
    )
    item.update(
        sample=sample,
        input_schema=_label_schema(input_schema(tool_id)),
        mode="local/dry_run",
        implementation_status="implemented",
    )
    return item


def catalog():
    return [
        tool_definition(item["id"])
        for item in static_catalog()
        if any(item["id"] in m.TOOL_IDS for m in _DOMAINS)
    ]
