"""Deterministic platform previews; inputs are supplied values, never file paths."""

from datetime import date, datetime
import hashlib
import json
import string
from app.decisions import digest as scope_digest, scope_approval, validity

TOOL_IDS = {f"T{i:02}" for i in range(1, 13)}
SAMPLES = {
    "T01": {
        "valid_at": "2027-03-01",
        "known_at": "2027-03-10",
        "facts": [
            {
                "field": "location",
                "value": "Berlin",
                "valid_from": "2027-01-01",
                "observed_at": "2027-02-01",
                "source": "export",
            }
        ],
    },
    "T02": {
        "rule": {
            "id": "R1",
            "version": "1",
            "status": "APPROVED",
            "predicate": {"field": "type", "op": "eq", "value": "end"},
        },
        "facts": {"type": "end"},
        "action": "review",
        "scope": "contracts",
        "approval": {
            "action": "review",
            "scope": "contracts",
            "rule_version": "1",
            "approved": True,
        },
    },
    "T03": {
        "now": "2027-03-01T12:00:00",
        "timer_at": "2027-03-01T11:00:00",
        "lease_until": "2027-03-01T11:30:00",
        "external_state": "UNKNOWN",
    },
    "T04": {
        "capabilities": [
            {
                "system": "HR",
                "action": "read",
                "scope": "records",
                "approved_scope": True,
                "probe_passed": True,
                "evidence": "probe-1",
            }
        ]
    },
    "T05": {
        "case_id": "C1",
        "step": "review",
        "revision": "1",
        "target": "HR",
        "payload": {"id": "C1"},
        "approval": {"approved": True, "rule_version": "1", "scope": "HR"},
        "rule_version": "1",
        "external_state": "NOT_STARTED",
    },
    "T06": {
        "expected": {"id": "P1", "date": "2027-01-01"},
        "observed": {"id": "P1", "date": "2027-01-01"},
        "evidence": {"source": "export", "independent": True, "reference": "E1"},
    },
    "T07": {
        "template": "Hallo {name}",
        "version": "1",
        "approved": True,
        "allowed_fields": ["name"],
        "facts": {"name": "Alex"},
    },
    "T08": {"text": "Ort: Berlin\nRolle: HR", "fields": ["Ort", "Rolle"]},
    "T09": {
        "scope": "contracts",
        "action": "read",
        "policy": {"approved": True, "scopes": ["contracts"], "actions": ["read"]},
        "records": [{"id": "A", "expires": "2027-01-01", "hold": False}],
        "as_of": "2027-02-01",
    },
    "T10": {
        "contents": {"db": "abc", "files": "def"},
        "manifest": {
            "db": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "files": "cb8379ac2098aa165029e3938a51da0bcecfc008fd6795f401178647f96c5b34",
        },
    },
    "T11": {
        "tests": [
            {"name": "dedupe", "result": "passed"},
            {"name": "unknown", "result": "passed"},
        ],
        "approval": True,
    },
    "T12": {
        "tools": [
            {"id": "O01", "implemented": True, "tested": True},
            {"id": "O02", "implemented": True, "tested": False},
        ]
    },
}


def _out(status, summary, data=None, checks=None, warnings=None, artifacts=None):
    return {
        "status": status,
        "summary": summary,
        "data": data or {},
        "checks": checks or [],
        "artifacts": artifacts or [],
        "warnings": warnings or [],
    }


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pred(r, f):
    field = r.get("field")
    op = r.get("op", "eq")
    if not field or op not in ("eq", "ne", "in", "exists"):
        raise ValueError("Unbekanntes Prädikat oder Feld")
    if op == "exists":
        return field in f and f[field] is not None
    if field not in f:
        return None
    if op == "eq":
        return f[field] == r.get("value")
    if op == "ne":
        return f[field] != r.get("value")
    if not isinstance(r.get("value"), list):
        raise ValueError("in erwartet Liste")
    return f[field] in r["value"]


def run(tool_id, payload):
    if tool_id not in TOOL_IDS:
        return _out("EXCEPTION", "Unbekanntes Werkzeug")
    try:
        return _run(tool_id, payload)
    except (KeyError, ValueError, TypeError, OverflowError) as e:
        return _out("EXCEPTION", "Eingabe ungültig", {"error": str(e)})


def _run(t, p):
    if t == "T01":
        if not p.get("valid_at") or not p.get("known_at"):
            return _out("NEEDS_DATA", "Gültigkeits- und Wissenszeitpunkt fehlen")
        valid = date.fromisoformat(p["valid_at"])
        known = date.fromisoformat(p["known_at"])
        eligible = []
        for f in p.get("facts", []):
            if (
                not all(
                    f.get(k) for k in ("field", "valid_from", "observed_at", "source")
                )
                or "value" not in f
                or f["value"] is None
            ):
                return _out("NEEDS_DATA", "Fakt ohne Wert, Herkunft oder Zeit")
            start = date.fromisoformat(f["valid_from"])
            obs = date.fromisoformat(f["observed_at"])
            end = date.fromisoformat(f["valid_to"]) if f.get("valid_to") else None
            if end is not None and end <= start:
                raise ValueError("Ungültiges Gültigkeitsintervall")
            if start <= valid and (end is None or valid < end) and obs <= known:
                eligible.append(f)
        latest = {}
        for f in eligible:
            key = f["field"]
            prior = latest.get(key)
            if not prior or f["observed_at"] > prior["observed_at"]:
                latest[key] = f
            elif f["observed_at"] == prior["observed_at"] and f.get(
                "value"
            ) != prior.get("value"):
                return _out(
                    "NEEDS_DECISION",
                    "Widersprüchliche Fakten gleicher Beobachtungszeit",
                    {"field": key},
                )
        return _out(
            "READY" if latest else "NEEDS_DATA",
            "Zeitbezogene Faktensicht berechnet",
            {"facts": latest},
        )
    if t == "T02":
        r = p.get("rule", {})
        action = p.get("action")
        fields = (
            "object_id",
            "revision",
            "action",
            "scope",
            "valid_from",
            "valid_to",
            "required_role",
        )
        if any(
            not isinstance(p.get(k), str) or not p[k].strip()
            for k in fields
            if k != "revision"
        ) or not (
            (type(p.get("revision")) is int and p["revision"] > 0)
            or (isinstance(p.get("revision"), str) and p["revision"].strip())
        ):
            return _out("NEEDS_DATA", "Entscheidungsumfang fehlt", {"authority": False})
        current = validity(p)
        if action not in ("read", "review", "draft", "export"):
            return _out("NEEDS_DECISION", "Unbekannte Aktion", {"authority": False})
        if (
            not isinstance(r, dict)
            or r.get("status") != "APPROVED"
            or not r.get("id")
            or not r.get("version")
            or not isinstance(r.get("predicate"), dict)
        ):
            return _out(
                "NEEDS_DECISION", "Freigegebene Regel fehlt", {"authority": False}
            )
        scope = {"schema": "T02/v1", **{k: p[k] for k in fields}, "rule": r}
        h, approved = scope_approval(scope, p.get("approval"))
        match = _pred(r["predicate"], p.get("facts", {}))
        authority = approved and current
        return _out(
            "NEEDS_DATA"
            if match is None
            else ("READY" if match and authority else "NEEDS_DECISION"),
            "Regel und lokale Freigabe geprüft",
            {"predicate_match": match, "authority": authority, "scope_hash": h},
            warnings=["Lokale Angaben belegen keine tatsächliche Rollenberechtigung."],
        )
    if t == "T03":
        if not p.get("now") or not p.get("timer_at"):
            return _out("NEEDS_DATA", "Zeitpunkte fehlen")
        now = datetime.fromisoformat(p["now"])
        timer = datetime.fromisoformat(p["timer_at"])
        lease = (
            datetime.fromisoformat(p["lease_until"]) if p.get("lease_until") else None
        )
        external = p.get("external_state", "UNKNOWN")
        unknown = external not in ("NOT_STARTED", "CONFIRMED", "FAILED")
        return _out(
            "NEEDS_DECISION" if unknown else "READY",
            "Timer und Lease bewertet",
            {
                "due": timer <= now,
                "lease_expired": lease <= now if lease else None,
                "external_state": "UNKNOWN" if unknown else external,
                "next_step": "abgleichen, nicht erneut senden"
                if unknown
                else "manuell prüfen",
            },
            warnings=["Kein Timer oder Worker ausgeführt."],
        )
    if t == "T04":
        cs = p.get("capabilities", [])
        if not cs:
            return _out(
                "NEEDS_DATA",
                "Keine Adapterfähigkeiten konfiguriert",
                {"capabilities": []},
            )
        rows = []
        for c in cs:
            proven = bool(
                c.get("system")
                and c.get("action")
                and c.get("scope")
                and c.get("approved_scope") is True
                and c.get("probe_passed") is True
                and c.get("evidence")
            )
            rows.append({**c, "status": "PROVEN" if proven else "UNVERIFIED"})
        return _out(
            "READY" if all(x["status"] == "PROVEN" for x in rows) else "NEEDS_DATA",
            "Gelieferte Fähigkeitsnachweise ausgewertet",
            {"capabilities": rows},
            warnings=["Keine Integration getestet."],
        )
    if t == "T05":
        fields = (
            "case_id",
            "step",
            "revision",
            "target",
            "payload",
            "rule_version",
            "valid_from",
            "valid_to",
            "required_role",
        )
        if (
            any(
                not isinstance(p.get(k), str) or not p[k].strip()
                for k in fields
                if k not in ("revision", "payload")
            )
            or not (
                (type(p.get("revision")) is int and p["revision"] > 0)
                or (isinstance(p.get("revision"), str) and p["revision"].strip())
            )
            or not isinstance(p.get("payload"), dict)
        ):
            return _out("NEEDS_DATA", "Intentdaten fehlen", {"authorized": False})
        current = validity(p)
        scope = {"schema": "T05/v1", **{k: p[k] for k in fields}}
        h, approved = scope_approval(scope, p.get("approval"))
        authorized = approved and current
        key = scope_digest([p["case_id"], p["step"], p["revision"], p["target"]])
        payload_hash = scope_digest(p["payload"])
        state = p.get("external_state", "UNKNOWN")
        unknown = state not in ("NOT_STARTED", "CONFIRMED", "FAILED")
        return _out(
            "NEEDS_DECISION" if not authorized or unknown else "READY",
            "Intentvorschau erstellt",
            {
                "idempotency_key": key,
                "payload_hash": payload_hash,
                "scope_hash": h,
                "authorized": authorized,
                "external_state": state,
                "next_step": "abgleichen" if unknown else "Freigabe und Ziel prüfen",
            },
            warnings=[
                "Lokale Angaben belegen keine tatsächliche Rollenberechtigung; nichts ausgeführt."
            ],
        )
    if t == "T06":
        expected = p.get("expected")
        observed = p.get("observed")
        evidence = p.get("evidence", {})
        if (
            not isinstance(expected, dict)
            or not expected
            or not isinstance(observed, dict)
        ):
            return _out("NEEDS_DATA", "Soll und Beobachtung erforderlich")
        if (
            evidence.get("independent") is not True
            or not evidence.get("source")
            or not evidence.get("reference")
        ):
            return _out("NEEDS_DATA", "Unabhängiger Zielbeleg fehlt")
        checks = [
            {
                "label": k,
                "passed": k in observed
                and type(observed[k]) is type(v)
                and observed[k] == v,
                "detail": "Soll und Ist stimmen überein"
                if k in observed and type(observed[k]) is type(v) and observed[k] == v
                else "Soll und Ist weichen ab oder fehlen",
            }
            for k, v in expected.items()
        ]
        return _out(
            "READY" if all(x["passed"] for x in checks) else "EXCEPTION",
            "Soll und unabhängige Beobachtung verglichen",
            {"evidence": evidence},
            checks,
        )
    if t == "T07":
        template = p.get("template")
        version = p.get("version")
        facts = p.get("facts", {})
        allowed = p.get("allowed_fields", [])
        if not template or not version or p.get("approved") is not True:
            return _out("NEEDS_DECISION", "Freigegebene versionierte Vorlage fehlt")
        fields = []
        for _, name, fmt, conversion in string.Formatter().parse(template):
            if name is not None:
                if not name.isidentifier() or fmt or conversion or name not in allowed:
                    raise ValueError("Nicht erlaubtes Vorlagenfeld")
                fields.append(name)
        missing = [f for f in fields if f not in facts or facts[f] is None]
        if missing:
            return _out("NEEDS_DATA", "Vorlagenfakten fehlen", {"missing": missing})
        content = template.format_map({f: str(facts[f]) for f in fields})
        digest = _hash(content)
        return _out(
            "READY",
            "Dokumententwurf reproduzierbar gerendert",
            {"version": version, "sha256": digest},
            artifacts=[
                {"name": "entwurf.txt", "content": content, "media_type": "text/plain"}
            ],
        )
    if t == "T08":
        text = p.get("text")
        fields = p.get("fields", [])
        if not isinstance(text, str) or not fields:
            return _out("NEEDS_DATA", "Text und erlaubte Felder erforderlich")
        if len(text) > 100000 or len(fields) > 50:
            raise ValueError("Eingabe überschreitet Begrenzung")
        candidates = []
        for line in text.splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() in fields:
                candidates.append(
                    {
                        "field": key.strip(),
                        "value": value.strip(),
                        "evidence": line,
                        "status": "CANDIDATE",
                    }
                )
        return _out(
            "NEEDS_DECISION" if candidates else "NEEDS_DATA",
            "Extraktionskandidaten zur Prüfung",
            {"candidates": candidates},
            warnings=["Kandidaten sind keine bestätigten Fakten."],
        )
    if t == "T09":
        scope = p.get("scope")
        action = p.get("action")
        policy = p.get("policy", {})
        if not scope or not action:
            return _out("NEEDS_DATA", "Aktion und Scope fehlen")
        if action not in ("read", "write", "export", "delete"):
            return _out(
                "NEEDS_DECISION",
                "Unbekannte Aktion ist nicht autorisiert",
                {"allowed": False},
            )
        allowed = (
            policy.get("approved") is True
            and scope in policy.get("scopes", [])
            and action in policy.get("actions", [])
        )
        if not allowed:
            return _out("NEEDS_DECISION", "Befugnis fehlt", {"allowed": False})
        if not p.get("as_of"):
            return _out(
                "NEEDS_DATA", "Stichtag für Aufbewahrung fehlt", {"allowed": True}
            )
        today = date.fromisoformat(p["as_of"])
        rows = []
        for r in p.get("records", []):
            expires = date.fromisoformat(r["expires"]) if r.get("expires") else None
            rows.append(
                {
                    "id": r.get("id"),
                    "eligible": bool(
                        expires and expires <= today and r.get("hold") is False
                    ),
                    "hold": r.get("hold"),
                    "expiry_known": bool(expires),
                }
            )
        return _out(
            "READY",
            "Zugriff und Aufbewahrung als Vorschau geprüft",
            {"allowed": True, "records": rows},
            warnings=["Keine Daten gelöscht oder Zugriff erteilt."],
        )
    if t == "T10":
        contents = p.get("contents", {})
        manifest = p.get("manifest", {})
        if not contents or not manifest:
            return _out("NEEDS_DATA", "Inhalte und Manifest erforderlich")
        keys = sorted(set(contents) | set(manifest))
        checks = []
        for k in keys:
            actual = (
                _hash(contents[k])
                if k in contents and isinstance(contents[k], str)
                else None
            )
            checks.append(
                {
                    "label": k,
                    "passed": actual is not None
                    and k in manifest
                    and actual == manifest[k],
                    "detail": "SHA-256 " + str(actual),
                }
            )
        return _out(
            "READY" if all(x["passed"] for x in checks) else "EXCEPTION",
            "Manifest gegen gelieferte Inhalte geprüft",
            {"entries": len(keys)},
            checks,
            warnings=["Keine Sicherung oder Wiederherstellung durchgeführt."],
        )
    if t == "T11":
        tests = p.get("tests", [])
        if not tests:
            return _out(
                "NEEDS_DATA",
                "Keine Testergebnisse geliefert",
                {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            )
        if any(x.get("result") not in ("passed", "failed", "skipped") for x in tests):
            raise ValueError("Unbekanntes Testergebnis")
        counts = {
            k: sum(x["result"] == k for x in tests)
            for k in ("passed", "failed", "skipped")
        }
        counts["total"] = len(tests)
        status = (
            "EXCEPTION"
            if counts["failed"]
            else (
                "NEEDS_DECISION"
                if counts["skipped"] or p.get("approval") is not True
                else "READY"
            )
        )
        return _out(
            status,
            "Gelieferte Testergebnisse und Rolloutfreigabe geprüft",
            counts,
            warnings=["Keine Tests oder Rollout ausgeführt."],
        )
    rows = p.get("tools", [])
    if not rows:
        return _out("NEEDS_DATA", "Werkzeugübersicht fehlt")
    return _out(
        "READY",
        "Umfang aus gelieferten Daten berechnet",
        {
            "total": len(rows),
            "implemented": sum(x.get("implemented") is True for x in rows),
            "tested": sum(x.get("tested") is True for x in rows),
            "tools": rows,
        },
        warnings=["Angaben wurden nicht unabhängig verifiziert."],
    )


# Synthetic samples carry deliberately pending local attestations.
for _id in ("T02", "T05"):
    SAMPLES[_id].update(
        {
            "valid_from": "2027-01-01",
            "valid_to": "2027-12-31",
            "as_of": "2027-03-01",
            "required_role": "HR",
            "approval": {},
        }
    )
SAMPLES["T02"].update({"object_id": "C1", "revision": "1"})
for _id, _fields in {
    "T02": (
        "object_id",
        "revision",
        "action",
        "scope",
        "valid_from",
        "valid_to",
        "required_role",
    ),
    "T05": (
        "case_id",
        "step",
        "revision",
        "target",
        "payload",
        "rule_version",
        "valid_from",
        "valid_to",
        "required_role",
    ),
}.items():
    _scope = {"schema": _id + "/v1", **{k: SAMPLES[_id][k] for k in _fields}}
    if _id == "T02":
        _scope["rule"] = SAMPLES[_id]["rule"]
    SAMPLES[_id]["approval"] = {
        "by": "synthetic-reviewer",
        "scope_hash": scope_digest(_scope),
    }
