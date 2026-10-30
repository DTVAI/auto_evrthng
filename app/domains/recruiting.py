"""Deterministic recruiting administration using only supplied local data."""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from email import policy
from email.parser import Parser
from zoneinfo import ZoneInfo
from app.decisions import decimal_value, scope_approval

TOOL_IDS = {f"R{i:02d}" for i in range(1, 16)}
ALLOWED = {
    "name",
    "email",
    "phone",
    "qualification",
    "experience",
    "availability",
    "location",
}


def _hash(x):
    return hashlib.sha256(
        json.dumps(x, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


def _need(p, *keys):
    missing = [
        k for k in keys if k not in p or p[k] is None or p[k] == "" or p[k] == []
    ]
    if missing:
        raise ValueError("Fehlende Angaben: " + ", ".join(missing))


def _res(
    data,
    summary="Lokale Auswertung erstellt.",
    status="READY",
    warnings=None,
    artifact=None,
):
    return {
        "status": status,
        "summary": summary,
        "data": data,
        "checks": [
            {
                "label": "Eingaben geprüft",
                "passed": status == "READY",
                "detail": summary,
            }
        ],
        "artifacts": [
            {"name": "entwurf.txt", "content": artifact, "media_type": "text/plain"}
        ]
        if artifact
        else [],
        "warnings": warnings or [],
    }


def _money(v):
    x = decimal_value(v)
    if not x.is_finite() or x < 0:
        raise ValueError("Betrag muss eine endliche nichtnegative Zahl sein.")
    return x


def _dt(v):
    d = datetime.fromisoformat(v)
    if d.tzinfo is None:
        raise ValueError("Zeitstempel benötigt Zeitzone.")
    return d


def run(tool_id, p):
    if tool_id not in TOOL_IDS:
        return _res({}, "Unbekanntes Werkzeug.", "NEEDS_DATA")
    try:
        if not isinstance(p, dict):
            raise ValueError("Eingabe muss ein Objekt sein.")
        if tool_id == "R01":
            _need(
                p,
                "branch",
                "role",
                "requested",
                "capacity",
                "occupied",
                "source",
                "requester_authorized",
            )
            requested = _money(p["requested"])
            capacity = _money(p["capacity"])
            occupied = _money(p["occupied"])
            remaining = capacity - occupied
            approved = p.get("approval_evidence")
            if p["requester_authorized"] is not True:
                return _res(
                    {"remaining": str(remaining)},
                    "Antragstellerbefugnis ungeklärt.",
                    "NEEDS_DECISION",
                )
            ok = requested <= remaining and bool(approved)
            return _res(
                {
                    "remaining": str(remaining),
                    "requested": str(requested),
                    "within_capacity": requested <= remaining,
                    "position_ready": ok,
                    "source": p["source"],
                },
                "Bedarf und freie Kapazität verglichen."
                if ok
                else "Freigabe oder Kapazität benötigt Entscheidung.",
                "READY" if ok else "NEEDS_DECISION",
            )
        if tool_id == "R02":
            _need(
                p,
                "position",
                "channel",
                "text",
                "budget",
                "committed",
                "spent",
                "price",
                "approval",
            )
            budget = _money(p["budget"])
            committed = _money(p["committed"])
            spent = _money(p["spent"])
            price = _money(p["price"])
            available = budget - committed - spent
            ok = bool(p["approval"]) and price <= available and not p.get("drift")
            text = f"Stelle: {p['position']}\nKanal: {p['channel']}\n\n{p['text']}"
            return _res(
                {
                    "available": str(available),
                    "price": str(price),
                    "budget_ok": price <= available,
                    "publication_ready": ok,
                    "draft": text,
                },
                "Kampagnenentwurf erstellt."
                if ok
                else "Budget, Freigabe oder Kanalabweichung prüfen.",
                "READY" if ok else "NEEDS_DECISION",
                warnings=["Keine Veröffentlichung oder Reservierung erfolgt."],
                artifact=text,
            )
        if tool_id == "R03":
            _need(p, "application_id", "received_at", "channel")
            _dt(p["received_at"])
            if "eml" in p:
                msg = Parser(policy=policy.default).parsestr(p["eml"])
                raw = {
                    "message_id": msg.get("Message-ID"),
                    "from": msg.get("From"),
                    "subject": msg.get("Subject"),
                    "body": msg.get_body(preferencelist=("plain",)).get_content()
                    if msg.is_multipart() and msg.get_body(preferencelist=("plain",))
                    else msg.get_content()
                    if not msg.is_multipart()
                    else "",
                    "attachments": [
                        {
                            "name": a.get_filename(),
                            "hash": hashlib.sha256(
                                a.get_payload(decode=True) or b""
                            ).hexdigest(),
                        }
                        for a in msg.iter_attachments()
                    ],
                }
            else:
                _need(p, "message")
                raw = p["message"]
            return _res(
                {
                    "application_id": p["application_id"],
                    "received_at": p["received_at"],
                    "channel": p["channel"],
                    "message": raw,
                    "raw_hash": _hash(p.get("eml", raw)),
                },
                "Bewerbung lokal erfasst.",
                warnings=["Keine Eingangsbestätigung versendet."],
            )
        if tool_id == "R04":
            _need(p, "fields", "required")
            extracted = {}
            issues = []
            for k, v in p["fields"].items():
                if k not in ALLOWED:
                    continue
                if (
                    not isinstance(v, dict)
                    or not v.get("source")
                    or v.get("value") in (None, "")
                ):
                    issues.append(k)
                    continue
                extracted[k] = {
                    "value": v["value"],
                    "source": v["source"],
                    "confirmed": False,
                }
            missing = [k for k in p["required"] if k not in extracted]
            issues += missing
            return _res(
                {
                    "fields": extracted,
                    "missing": missing,
                    "issues": sorted(set(issues)),
                },
                "Felder mit Fundstellen extrahiert."
                if not issues
                else "Erforderliche Felder oder Fundstellen fehlen.",
                "READY" if not issues else "NEEDS_DATA",
            )
        if tool_id == "R05":
            _need(p, "application_id", "identifiers", "candidates")
            if (
                not isinstance(p["identifiers"], dict)
                or not p["identifiers"]
                or not isinstance(p["candidates"], list)
            ):
                raise ValueError("Identifikatoren und Kandidaten erforderlich")
            matches, contradictions = [], []
            for candidate in p["candidates"]:
                identifiers = candidate.get("identifiers", {})
                common = [
                    k for k, v in p["identifiers"].items() if v and identifiers.get(k)
                ]
                equal = any(identifiers[k] == p["identifiers"][k] for k in common)
                conflict = any(identifiers[k] != p["identifiers"][k] for k in common)
                if equal:
                    matches.append(candidate)
                    if conflict:
                        contradictions.append(candidate)
            confirmed = bool(
                p.get("identity_evidence")
                and p.get("person_confirmation")
                and len(matches) == 1
                and not contradictions
            )
            return _res(
                {
                    "application_id": p["application_id"],
                    "candidates": matches,
                    "contradictions": contradictions,
                    "confirmed_person": matches[0].get("person_id")
                    if confirmed
                    else None,
                },
                "Identität belegt."
                if confirmed
                else "Identitätszuordnung menschlich prüfen.",
                "READY" if confirmed else "NEEDS_DECISION",
            )
        if tool_id == "R06":
            _need(
                p,
                "approved_fields",
                "existing_records",
                "identifier",
                "action",
                "source_id",
            )
            allowed = {
                "create": {"name", "email", "phone", "location"},
                "update": {"name", "email", "phone", "location"},
            }
            fields = p["approved_fields"]
            if (
                p["action"] not in allowed
                or not all(
                    isinstance(p[k], str) and p[k].strip()
                    for k in ("identifier", "source_id")
                )
                or not isinstance(fields, dict)
                or not fields
                or not isinstance(p["existing_records"], list)
            ):
                raise ValueError("Ungültiger Auftrag")
            if set(fields) - allowed[p["action"]] or any(
                not isinstance(v, str) or not v.strip() for v in fields.values()
            ):
                raise ValueError("Feld oder Feldtyp für Aktion nicht zugelassen")
            scope = {
                "schema": "R06/v1",
                "identifier": p["identifier"],
                "action": p["action"],
                "source_id": p["source_id"],
                "approved_fields": fields,
            }
            h, approved = scope_approval(scope, p.get("decision"))
            matches = [
                x
                for x in p["existing_records"]
                if x.get("identifier") == p["identifier"]
            ]
            identity_ok = len(matches) == (0 if p["action"] == "create" else 1)
            readback = p.get("observed_fields", p.get("readback"))
            if readback is not None and not isinstance(readback, dict):
                raise ValueError("Rücklesung muss ein Objekt sein")
            diffs = {
                k: {"expected": v, "actual": readback.get(k)}
                for k, v in fields.items()
                if readback is not None
                and (
                    k not in readback
                    or type(readback[k]) is not type(v)
                    or readback[k] != v
                )
            }
            verified = (
                readback is not None and not diffs and bool(p.get("readback_evidence"))
            )
            ready = approved and identity_ok and verified
            return _res(
                {
                    "matches": matches,
                    "scope_hash": h,
                    "manual_handoff": fields if approved and identity_ok else None,
                    "prepared": approved and identity_ok,
                    "readback_differences": diffs,
                    "readback_present": readback is not None,
                    "readback_confirmed": verified,
                },
                "Manuellen HR-Abgleich geprüft.",
                "READY" if ready else "NEEDS_DECISION",
                warnings=[
                    "Lokale Angaben; keine HR-Systemanbindung oder Schreibaktion."
                ],
            )
        if tool_id == "R07":
            _need(p, "case_id", "required_fields", "answers", "template")
            answered = {
                x.get("field")
                for x in p["answers"]
                if x.get("case_id") == p["case_id"]
                and x.get("source")
                and x.get("complete") is True
            }
            missing = [x for x in p["required_fields"] if x not in answered]
            text = p["template"] + "\n" + "\n".join("- " + str(x) for x in missing)
            return _res(
                {"missing": missing, "answered": sorted(answered), "draft": text},
                "Fehlende Angaben zusammengestellt.",
                warnings=["Empfänger und Vorlage vor manueller Verwendung prüfen."],
                artifact=text if missing else None,
            )
        if tool_id == "R08":
            _need(p, "submissions")
            out = []
            for s in p["submissions"]:
                _need(s, "agency", "message_id", "profile_hash", "received_at")
                _dt(s["received_at"])
                out.append(s)
            hashes = {x["profile_hash"] for x in out}
            return _res(
                {
                    "submissions": out,
                    "same_profile_hash": len(hashes) == 1,
                    "identity_confirmed": False,
                    "cost_acknowledged": False,
                },
                "Vorstellungen mit Quellen getrennt dargestellt.",
                "NEEDS_DECISION" if len(out) > 1 else "READY",
                warnings=["Kein automatischer Identitäts- oder Kostenentscheid."],
            )
        if tool_id == "R09":
            _need(
                p,
                "application_id",
                "position_branch",
                "role_mapping",
                "fields",
                "purpose",
            )
            mapping = p["role_mapping"]
            ok = (
                mapping.get("branch") == p["position_branch"]
                and mapping.get("valid") is True
                and mapping.get("address")
            )
            fields = {
                k: v
                for k, v in p["fields"].items()
                if k in ALLOWED
                and isinstance(v, dict)
                and v.get("confirmed") is True
                and v.get("source")
            }
            return _res(
                {
                    "application_id": p["application_id"],
                    "destination": mapping.get("address") if ok else None,
                    "fields": fields,
                    "purpose": p["purpose"],
                },
                "Minimiertes Profil für manuelle Übergabe erstellt."
                if ok
                else "Zuständige Niederlassung oder Adresse ungeklärt.",
                "READY" if ok else "NEEDS_DECISION",
                warnings=["Keine Übermittlung erfolgt."],
            )
        if tool_id == "R10":
            _need(p, "application_id", "start", "end", "busy", "recipients")
            start = _dt(p["start"]).astimezone(timezone.utc)
            end = _dt(p["end"]).astimezone(timezone.utc)
            if end <= start:
                raise ValueError("Terminende muss nach Beginn liegen.")
            collisions = []
            for b in p["busy"]:
                bs = _dt(b["start"]).astimezone(timezone.utc)
                be = _dt(b["end"]).astimezone(timezone.utc)
                if be <= bs:
                    raise ValueError("Ungültiges Belegtintervall.")
                if start < be and bs < end:
                    collisions.append(b)
            confirmed = (
                p.get("candidate_confirmed") is True
                and p.get("branch_confirmed") is True
                and all(
                    isinstance(x, dict)
                    and x.get("address")
                    and x.get("verified") is True
                    and x.get("application_id") == p["application_id"]
                    for x in p["recipients"]
                )
                and {x.get("role") for x in p["recipients"]} >= {"candidate", "branch"}
            )
            return _res(
                {
                    "start_berlin": start.astimezone(
                        ZoneInfo("Europe/Berlin")
                    ).isoformat(),
                    "end_berlin": end.astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
                    "collisions": collisions,
                    "confirmed": confirmed,
                },
                "Termin kollidiert oder Bestätigung fehlt."
                if collisions or not confirmed
                else "Termin lokal geprüft.",
                "NEEDS_DECISION" if collisions or not confirmed else "READY",
                warnings=["Kein Kalendereintrag erstellt."],
            )
        if tool_id == "R11":
            _need(p, "application_id", "feedback", "decision")
            d = p["decision"]
            valid = d.get("state") in ("open", "further_interview", "hire", "decline")
            if not valid:
                raise ValueError("Unbekannter Entscheidungsstatus.")
            authorized = d["state"] == "open" or bool(
                d.get("authorized_person") and d.get("source") and d.get("revision")
            )
            return _res(
                {
                    "application_id": p["application_id"],
                    "feedback": p["feedback"],
                    "decision": d if authorized else {"state": "open"},
                    "next_action": {
                        "open": "Rückmeldung einholen",
                        "further_interview": "Termin manuell planen",
                        "hire": "Startvorbereitung prüfen",
                        "decline": "Freigabe für Mitteilung prüfen",
                    }[d["state"]]
                    if authorized
                    else "Entscheidung belegen",
                },
                "Menschliche Entscheidung dokumentiert."
                if authorized
                else "Entscheidungsbeleg fehlt.",
                "READY" if authorized else "NEEDS_DECISION",
                warnings=["Keine Auswahl oder Kommunikation automatisiert."],
            )
        if tool_id == "R12":
            _need(p, "application_id", "purpose", "authorized", "facts")
            if p["authorized"] is not True:
                return _res({}, "Zugriff nicht bestätigt.", "NEEDS_DECISION")
            facts = [
                f for f in p["facts"] if f.get("source") and f.get("confirmed") is True
            ]
            return _res(
                {
                    "application_id": p["application_id"],
                    "facts": facts,
                    "open_questions": p.get("open_questions", []),
                    "purpose": p["purpose"],
                },
                "Gesprächsüberblick aus belegten Fakten erstellt.",
                warnings=["Keine Eignungsbewertung."],
            )
        if tool_id == "R13":
            _need(p, "revision", "decision_evidence", "checklist")
            required = {
                "identity",
                "position",
                "contract",
                "hr_record",
                "workplace",
                "it",
                "start_plan",
            }
            items = p["checklist"]
            missing = sorted(required - set(items))
            blockers = [
                k
                for k in required & set(items)
                if not isinstance(items[k], dict)
                or items[k].get("confirmed") is not True
                or not items[k].get("evidence")
                or items[k].get("revision") != p["revision"]
            ]
            ready = not missing and not blockers and p.get("hr_confirmation") is True
            return _res(
                {
                    "ready_for_start": ready,
                    "missing": missing,
                    "blockers": blockers,
                    "revision": p["revision"],
                },
                "Startbereitschaft belegt."
                if ready
                else "Startbereitschaft hat offene Prüfungen.",
                "READY" if ready else "NEEDS_DATA",
                warnings=["Keine Lohn- oder Abrechnungsübermittlung."],
            )
        if tool_id == "R14":
            _need(p, "old_date", "new_date", "source", "dependencies")
            old = date.fromisoformat(p["old_date"])
            new = date.fromisoformat(p["new_date"])
            if old == new:
                raise ValueError("Altes und neues Datum sind gleich.")
            approved = bool(p.get("approval_evidence") and p.get("candidate_consent"))
            affected = [
                x
                for x in p["dependencies"]
                if x.get("date_dependent") is True
                and x.get("kind") not in ("payroll", "abrechnung")
            ]
            return _res(
                {
                    "old_date": old.isoformat(),
                    "requested_date": new.isoformat(),
                    "effective_date": new.isoformat() if approved else old.isoformat(),
                    "affected": affected,
                    "readiness_review_required": True,
                },
                "Datumsänderung mit Abhängigkeiten vorbereitet."
                if approved
                else "Freigabe und Zustimmung sind erforderlich.",
                "READY" if approved else "NEEDS_DECISION",
                warnings=["Keine Systemänderung oder Abrechnungsübermittlung."],
            )
        if tool_id == "R15":
            _need(
                p,
                "old",
                "new",
                "authorized",
                "purpose",
                "identity_confirmed",
                "retention_valid",
            )
            if not all(
                p[k] is True
                for k in ("authorized", "identity_confirmed", "retention_valid")
            ):
                return _res(
                    {},
                    "Berechtigung, Identität oder Aufbewahrung ungeklärt.",
                    "NEEDS_DECISION",
                )
            changes = []
            for k in sorted((set(p["old"]) | set(p["new"])) & ALLOWED):
                a = p["old"].get(k)
                b = p["new"].get(k)
                if a != b:
                    changes.append({"field": k, "old": a, "new": b})
            return _res(
                {"changes": changes, "purpose": p["purpose"]},
                "Profilstände neutral verglichen.",
                warnings=["Keine Bewertung oder Rangfolge."],
            )
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        InvalidOperation,
        OverflowError,
    ) as e:
        return _res({}, "Ungültige oder fehlende Eingaben: " + str(e), "NEEDS_DATA")


SAMPLES = {
    "R01": {
        "branch": "Nord",
        "role": "Assistenz",
        "requested": "1",
        "capacity": "3",
        "occupied": "1",
        "source": "Antrag",
        "requester_authorized": True,
        "approval_evidence": "Freigabe 1",
    },
    "R02": {
        "position": "Assistenz Nord",
        "channel": "Portal",
        "text": "Wir suchen Unterstützung.",
        "budget": "1000",
        "committed": "100",
        "spent": "100",
        "price": "200",
        "approval": "Freigabe 1",
    },
    "R03": {
        "application_id": "a1",
        "received_at": "2026-10-01T12:00:00+02:00",
        "channel": "mail",
        "message": {"subject": "Bewerbung", "body": "Hallo"},
    },
    "R04": {
        "fields": {"name": {"value": "Alex", "source": "CV Seite 1"}},
        "required": ["name"],
    },
    "R05": {
        "application_id": "a1",
        "identifiers": {"email": "a@example.org"},
        "candidates": [{"person_id": "p1", "identifiers": {"email": "a@example.org"}}],
        "identity_evidence": "Ausweis geprüft",
        "person_confirmation": "Bestätigung",
    },
    "R06": {
        "approved_fields": {"name": "Alex"},
        "existing_records": [{"identifier": "p1"}],
        "identifier": "p1",
        "action": "update",
        "source_id": "a1",
        "decision": {},
    },
    "R07": {
        "case_id": "a1",
        "required_fields": ["Telefon", "Verfügbarkeit"],
        "answers": [
            {"case_id": "a1", "field": "Telefon", "source": "m1", "complete": True}
        ],
        "template": "Bitte ergänzen:",
    },
    "R08": {
        "submissions": [
            {
                "agency": "Agentur A",
                "message_id": "m1",
                "profile_hash": "abc",
                "received_at": "2026-10-01T12:00:00+02:00",
            }
        ]
    },
    "R09": {
        "application_id": "a1",
        "position_branch": "Nord",
        "role_mapping": {"branch": "Nord", "valid": True, "address": "hr@example.org"},
        "fields": {"name": {"value": "Alex", "confirmed": True, "source": "CV"}},
        "purpose": "Vorstellung",
    },
    "R10": {
        "application_id": "a1",
        "recipients": [
            {
                "role": "candidate",
                "address": "a@example.org",
                "verified": True,
                "application_id": "a1",
            },
            {
                "role": "branch",
                "address": "n@example.org",
                "verified": True,
                "application_id": "a1",
            },
        ],
        "start": "2026-11-01T10:00:00+01:00",
        "end": "2026-11-01T11:00:00+01:00",
        "busy": [
            {"start": "2026-11-01T11:00:00+01:00", "end": "2026-11-01T12:00:00+01:00"}
        ],
        "candidate_confirmed": True,
        "branch_confirmed": True,
    },
    "R11": {
        "application_id": "a1",
        "feedback": "Gespräch geführt",
        "decision": {"state": "open"},
    },
    "R12": {
        "application_id": "a1",
        "purpose": "Gespräch",
        "authorized": True,
        "facts": [{"value": "Abschluss 2021", "source": "CV", "confirmed": True}],
    },
    "R13": {
        "revision": "1",
        "decision_evidence": "Freigabe",
        "checklist": {
            x: {"confirmed": True, "evidence": "Beleg " + x, "revision": "1"}
            for x in (
                "identity",
                "position",
                "contract",
                "hr_record",
                "workplace",
                "it",
                "start_plan",
            )
        },
        "hr_confirmation": True,
    },
    "R14": {
        "old_date": "2026-11-01",
        "new_date": "2026-11-15",
        "source": "m1",
        "dependencies": [{"kind": "it", "date_dependent": True}],
        "approval_evidence": "NL",
        "candidate_consent": "m2",
    },
    "R15": {
        "old": {"qualification": {"value": "2020", "source": "CV1"}},
        "new": {"qualification": {"value": "2021", "source": "CV2"}},
        "authorized": True,
        "purpose": "Aktiver Fall",
        "identity_confirmed": True,
        "retention_valid": True,
    },
}
_r06 = SAMPLES["R06"]
_r06_scope = {
    "schema": "R06/v1",
    **{k: _r06[k] for k in ("identifier", "action", "source_id", "approved_fields")},
}
_r06["decision"] = {
    "by": "synthetic-reviewer",
    "scope_hash": scope_approval(_r06_scope, {})[0],
}
_r06["observed_fields"] = dict(_r06["approved_fields"])
_r06["readback_evidence"] = "synthetic manual attestation"
