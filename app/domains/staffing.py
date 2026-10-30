"""Local staffing requests, evidence and reconciliation previews."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from .personnel import result, check, require, dec, period, day, digest, approval

TOOL_IDS = {f"A{i:02}" for i in range(1, 9)}


def lines(items, fields):
    if not isinstance(items, list) or not items:
        raise ValueError("Positionen fehlen")
    seen = set()
    for x in items:
        require(x, fields)
        if x["id"] in seen:
            raise ValueError("Doppelte Positions-ID: " + str(x["id"]))
        seen.add(x["id"])
    return {x["id"]: x for x in items}


def money(value):
    return dec(value).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


def run(tool_id, payload):
    if tool_id not in TOOL_IDS:
        return result("EXCEPTION", "Unbekanntes Werkzeug.")
    try:
        if not isinstance(payload, dict):
            raise ValueError("Eingabe muss ein Objekt sein")
        p = payload
        if tool_id == "A01":
            fields = [
                "branch",
                "cost_center",
                "owner",
                "role",
                "requirements",
                "reason",
                "start",
                "end",
                "hours",
                "shift",
                "supplier",
            ]
            require(p, fields)
            period(p["start"], p["end"])
            hours = dec(p["hours"])
            if hours <= 0:
                raise ValueError("Stunden müssen positiv sein")
            scope = {k: p[k] for k in fields}
            h, ok = approval(p, scope)
            text = "Bedarfsanfrage\n" + "\n".join(f"{k}: {scope[k]}" for k in fields)
            return result(
                "READY" if ok else "NEEDS_DECISION",
                "Bedarfsanfrage vorbereitet.",
                {"scope_hash": h, "request": scope},
                [check("Bedarfs- und Budgetfreigabe", ok, h)],
                [
                    {
                        "name": "bedarfsanfrage.txt",
                        "content": text,
                        "media_type": "text/plain",
                    }
                ],
                ["Versand erfolgt manuell; keine Bestellung."],
            )
        if tool_id == "A02":
            require(p, ["request_revision", "offers"])
            offers = []
            seen = set()
            for o in p["offers"]:
                require(
                    o,
                    [
                        "id",
                        "supplier",
                        "candidate",
                        "start",
                        "end",
                        "hours",
                        "rate",
                        "extra_cost",
                    ],
                )
                if o["id"] in seen:
                    raise ValueError("Doppeltes Angebot: " + str(o["id"]))
                seen.add(o["id"])
                period(o["start"], o["end"])
                hours, rate, extra = (
                    dec(o["hours"]),
                    dec(o["rate"]),
                    dec(o["extra_cost"]),
                )
                if min(hours, rate, extra) < 0:
                    raise ValueError("Negative Kosten oder Stunden")
                offers.append(
                    {
                        "id": o["id"],
                        "supplier": o["supplier"],
                        "candidate": o["candidate"],
                        "estimated_cost": str(money(hours * rate + extra)),
                        "start": o["start"],
                        "end": o["end"],
                    }
                )
            return result(
                "READY",
                "Angebote sachlich verglichen; Auswahl bleibt beim Menschen.",
                {"request_revision": p["request_revision"], "offers": offers},
            )
        if tool_id == "A03":
            fields = [
                "offer_id",
                "offer_revision",
                "selection_evidence",
                "supplier",
                "candidate",
                "location",
                "role",
                "start",
                "end",
                "hours",
                "rate",
                "rules_version",
            ]
            require(p, fields)
            period(p["start"], p["end"])
            hours, rate = dec(p["hours"]), dec(p["rate"])
            if hours <= 0 or rate < 0:
                raise ValueError("Stunden müssen positiv und Satz nichtnegativ sein")
            for value, limit in (
                (hours, p.get("max_hours")),
                (rate, p.get("max_rate")),
            ):
                if limit is not None and (dec(limit) < 0 or value > dec(limit)):
                    raise ValueError("Konfigurierte Grenze überschritten")
            scope = {k: p[k] for k in fields}
            h, ok = approval(p, scope)
            return result(
                "READY" if ok else "NEEDS_DECISION",
                "Bestellung als Entwurf vorbereitet.",
                {"scope_hash": h, "order": scope},
                [check("Einsatz- und Kostenfreigabe", ok, h)],
                warnings=[
                    "Externe Bestellung und rechtliche Prüfung erfolgen manuell."
                ],
            )
        if tool_id == "A04":
            require(p, ["order_revision", "start", "end", "requirements", "documents"])
            a, b = period(p["start"], p["end"])
            issues = []
            for req in p["requirements"]:
                matches = [
                    x
                    for x in p["documents"]
                    if x.get("type") == req
                    and x.get("order_revision") == p["order_revision"]
                ]
                if not matches:
                    issues.append(f"{req}: Nachweis fehlt")
                    continue
                valid = False
                for x in matches:
                    require(x, ["valid_from", "valid_until"])
                    d, e = period(x["valid_from"], x["valid_until"])
                    valid |= d <= a and e >= b
                if not valid:
                    issues.append(f"{req}: Gültigkeit deckt Einsatz nicht ab")
            return result(
                "READY" if not issues else "NEEDS_DECISION",
                "Einsatzunterlagen geprüft.",
                {"issues": issues},
                [
                    check(
                        "Nachweise",
                        not issues,
                        "; ".join(issues) or "Zeitraum abgedeckt",
                    )
                ],
                warnings=["Keine rechtliche Bewertung."],
            )
        if tool_id == "A05":
            require(p, ["person_id", "start", "end", "supplier_lines", "time_lines"])
            start, end = period(p["start"], p["end"])
            supplier = lines(p["supplier_lines"], ["id", "date", "hours", "approved"])
            internal = lines(p["time_lines"], ["id", "date", "hours"])
            rows = []
            for key in sorted(set(supplier) | set(internal)):
                s, t = supplier.get(key), internal.get(key)
                ok = bool(
                    s
                    and t
                    and s["date"] == t["date"]
                    and dec(s["hours"]) == dec(t["hours"])
                    and s["approved"] is True
                )
                if s and (not start <= day(s["date"]) <= end or dec(s["hours"]) < 0):
                    ok = False
                if t and (not start <= day(t["date"]) <= end or dec(t["hours"]) < 0):
                    ok = False
                rows.append({"id": key, "supplier": s, "time": t, "matched": ok})
            return result(
                "READY" if all(x["matched"] for x in rows) else "NEEDS_DECISION",
                "Stunden positionsweise verglichen.",
                {"lines": rows},
                [
                    check(
                        "Alle Positionen abgestimmt",
                        all(x["matched"] for x in rows),
                        len(rows),
                    )
                ],
            )
        if tool_id == "A06":
            require(
                p,
                [
                    "supplier",
                    "invoice_number",
                    "order_revision",
                    "invoice_lines",
                    "confirmed_lines",
                ],
            )
            if "existing_invoices" not in p or not isinstance(
                p["existing_invoices"], list
            ):
                raise ValueError("existing_invoices fehlt")
            inv = lines(p["invoice_lines"], ["id", "hours", "rate", "amount"])
            confirmed = lines(p["confirmed_lines"], ["id", "hours", "rate"])
            duplicate = any(
                x.get("supplier") == p["supplier"]
                and x.get("invoice_number") == p["invoice_number"]
                for x in p["existing_invoices"]
            )
            rows = []
            for key in sorted(set(inv) | set(confirmed)):
                i, c = inv.get(key), confirmed.get(key)
                issues = []
                if not i or not c:
                    issues.append("Position fehlt")
                else:
                    ih, ir, amount = dec(i["hours"]), dec(i["rate"]), dec(i["amount"])
                    ch, cr = dec(c["hours"]), dec(c["rate"])
                    if min(ih, ir, amount, ch, cr) < 0:
                        raise ValueError("Negative Rechnungswerte")
                    if ih != ch:
                        issues.append("Stunden weichen ab")
                    if ir != cr:
                        issues.append("Satz weicht ab")
                    if amount != money(ih * ir):
                        issues.append("Positionsbetrag weicht von HALF_UP-Rundung ab")
                rows.append(
                    {
                        "id": key,
                        "issues": issues,
                        "expected_amount": str(money(dec(c["hours"]) * dec(c["rate"])))
                        if c
                        else None,
                    }
                )
            ok = not duplicate and all(not x["issues"] for x in rows)
            return result(
                "READY" if ok else "NEEDS_DECISION",
                "Rechnung positionsweise geprüft.",
                {"duplicate": duplicate, "lines": rows},
                [
                    check(
                        "Keine doppelte Rechnung", not duplicate, p["invoice_number"]
                    ),
                    check("Positionen", all(not x["issues"] for x in rows), len(rows)),
                ],
                warnings=["Keine Buchung oder Zahlung ausgelöst."],
            )
        if tool_id == "A07":
            require(
                p,
                [
                    "dispute_id",
                    "reason",
                    "line_ids",
                    "invoice_number",
                    "correction_route",
                    "recipient",
                    "status",
                ],
            )
            valid = p["status"] in ("open", "requested", "received", "resolved")
            if not valid:
                raise ValueError("Unbekannter Reklamationsstatus")
            evidence = bool(p.get("resolution_evidence"))
            ok = p["status"] == "resolved" and evidence
            return result(
                "READY" if ok else "NEEDS_DECISION",
                "Reklamationsstand geprüft.",
                {
                    "dispute_id": p["dispute_id"],
                    "line_ids": p["line_ids"],
                    "next_step": "Nachweis prüfen und Korrektur abstimmen"
                    if not ok
                    else "Abschluss dokumentieren",
                },
                [check("Korrektur belegt", ok, "Abschluss benötigt Nachweis")],
                warnings=["Kommunikation erfolgt manuell."],
            )
        if tool_id == "A08":
            require(
                p,
                [
                    "order_revision",
                    "action",
                    "current_start",
                    "current_end",
                    "reason",
                    "open_items",
                ],
            )
            a, b = period(p["current_start"], p["current_end"])
            if p["action"] not in ("extend", "end"):
                raise ValueError("action muss extend oder end sein")
            scope = {
                k: p[k]
                for k in (
                    "order_revision",
                    "action",
                    "current_start",
                    "current_end",
                    "reason",
                )
            }
            if p["action"] == "extend":
                require(p, ["new_end"])
                new = day(p["new_end"])
                if new <= b:
                    raise ValueError("Neues Ende muss nach bisherigem Ende liegen")
                scope["new_end"] = p["new_end"]
            h, ok = approval(p, scope)
            pending = [x for x in p["open_items"] if not x.get("confirmed")]
            return result(
                "READY" if ok and not pending else "NEEDS_DECISION",
                "Einsatzänderung und offene Aufgaben geprüft.",
                {"scope_hash": h, "pending_items": pending},
                [
                    check("Freigabe", ok, h),
                    check("Aufgaben abgeschlossen", not pending, len(pending)),
                ],
                warnings=["Keine rechtliche Wirkung oder externe Änderung abgeleitet."],
            )
    except (ValueError, TypeError, KeyError, InvalidOperation, AttributeError) as exc:
        return result("NEEDS_DATA", str(exc))


SAMPLES = {
    "A01": {
        "branch": "Berlin",
        "cost_center": "K1",
        "owner": "HR",
        "role": "Assistenz",
        "requirements": ["Office"],
        "reason": "Engpass",
        "start": "2026-01-01",
        "end": "2026-03-31",
        "hours": "40",
        "shift": "Tag",
        "supplier": "D1",
    },
    "A02": {
        "request_revision": "1",
        "offers": [
            {
                "id": "O1",
                "supplier": "D1",
                "candidate": "C1",
                "start": "2026-01-01",
                "end": "2026-03-31",
                "hours": "160",
                "rate": "35.50",
                "extra_cost": "10",
            }
        ],
    },
    "A03": {
        "offer_id": "O1",
        "offer_revision": "1",
        "selection_evidence": "E1",
        "supplier": "D1",
        "candidate": "C1",
        "location": "Berlin",
        "role": "Assistenz",
        "start": "2026-01-01",
        "end": "2026-03-31",
        "hours": "160",
        "rate": "35.50",
        "rules_version": "1",
    },
    "A04": {
        "order_revision": "1",
        "start": "2026-01-01",
        "end": "2026-03-31",
        "requirements": ["Qualifikation"],
        "documents": [
            {
                "type": "Qualifikation",
                "order_revision": "1",
                "valid_from": "2025-01-01",
                "valid_until": "2026-12-31",
            }
        ],
    },
    "A05": {
        "person_id": "C1",
        "start": "2026-01-01",
        "end": "2026-01-31",
        "supplier_lines": [
            {"id": "L1", "date": "2026-01-02", "hours": "8", "approved": True}
        ],
        "time_lines": [{"id": "L1", "date": "2026-01-02", "hours": "8"}],
    },
    "A06": {
        "supplier": "D1",
        "invoice_number": "I1",
        "order_revision": "1",
        "invoice_lines": [
            {"id": "L1", "hours": "8", "rate": "35.50", "amount": "284.00"}
        ],
        "confirmed_lines": [{"id": "L1", "hours": "8", "rate": "35.50"}],
        "existing_invoices": [],
    },
    "A07": {
        "dispute_id": "D1",
        "reason": "Stunden",
        "line_ids": ["L1"],
        "invoice_number": "I1",
        "correction_route": "Gutschrift",
        "recipient": "D1",
        "status": "open",
    },
    "A08": {
        "order_revision": "1",
        "action": "extend",
        "current_start": "2026-01-01",
        "current_end": "2026-03-31",
        "new_end": "2026-04-30",
        "reason": "Bedarf",
        "open_items": [{"name": "Unterlagen", "confirmed": True}],
    },
}
