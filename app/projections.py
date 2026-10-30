"""Expected target values for manual attestations; never asserts external execution."""

# Explicit projections only: tools without a defined target cannot be completed.
FIELDS = {
    "P01": ("person_id", "new", "unit", "valid_from", "valid_to"),
    "P02": ("person_id", "new", "unit", "valid_from", "valid_to"),
    "P04": ("person_id", "fact_id", "new", "valid_from", "valid_to"),
    "A06": ("supplier", "invoice_number", "order_revision", "invoice_lines"),
    "A05": ("person_id", "start", "end", "time_lines"),
    "A07": ("dispute_id", "invoice_number", "line_ids", "status"),
    "O13": ("commitments",),
}


def expected(tool_id, payload, subject_id=None):
    if tool_id == "T1":
        return payload
    if subject_id is not None:
        # A case linked to a person must not attest a different person, even
        # where the domain nests identity under an event or list of records.
        found = []

        def identities(value):
            if isinstance(value, dict):
                if "person_id" in value:
                    found.append(value["person_id"])
                for child in value.values():
                    identities(child)
            elif isinstance(value, list):
                for child in value:
                    identities(child)

        identities(payload)
        if found and any(person != subject_id for person in found):
            return None
    if tool_id == "O01":
        from .services import evaluate

        event = payload.get("event", {})
        tasks = evaluate(tool_id, payload).get("data", {}).get("tasks")
        return (
            {
                "event": {
                    k: event[k]
                    for k in ("person_id", "date", "source", "event_id", "revision")
                    if k in event
                },
                "tasks": tasks,
            }
            if event and tasks
            else None
        )
    if tool_id == "O02":
        from .services import evaluate

        schedule = evaluate(tool_id, payload).get("data", {}).get("schedule")
        return (
            {"target_date": payload.get("target_date"), "schedule": schedule}
            if schedule
            else None
        )
    if tool_id in ("P05", "P12"):
        from .services import evaluate

        result = evaluate(tool_id, payload)
        document_hash = result.get("data", {}).get("document_hash")
        return {"document_hash": document_hash} if document_hash else None
    if tool_id == "P03":
        from .services import evaluate

        rows = evaluate(tool_id, payload).get("data", {}).get("people", [])
        return (
            {
                "valid_from": payload.get("valid_from"),
                "people": [
                    {"person_id": row["person_id"], "new": row["new"]} for row in rows
                ],
            }
            if rows
            else None
        )
    if tool_id == "P07":
        from .services import evaluate

        data = evaluate(tool_id, payload).get("data", {})
        return (
            {
                "person_id": payload.get("person_id"),
                "draft_hash": data.get("draft_hash"),
                "scope_hash": data.get("scope_hash"),
            }
            if data.get("draft_hash")
            else None
        )
    if tool_id == "M07":
        from .services import evaluate

        draft = evaluate(tool_id, payload).get("data", {}).get("draft")
        return {"draft": draft} if draft is not None else None
    fields = FIELDS.get(tool_id)
    if not fields:
        # For calculators without a distinct external target, attest the local
        # result itself and relevant identity/date fields. This is not a claim
        # that an external system was updated.
        from .services import evaluate

        data = evaluate(tool_id, payload).get("data", {})
        target = {
            k: v
            for k, v in data.items()
            if k not in {"snapshot", "scope", "input", "payload"}
        }
        identity = {
            k: payload[k]
            for k in (
                "person_id",
                "case_id",
                "application_id",
                "valid_from",
                "valid_to",
                "effective_date",
                "date",
                "revision",
            )
            if k in payload
        }
        return {"identity": identity, "local_result": target} if target else None
    target = {key: payload[key] for key in fields if key in payload}
    if (
        subject_id is not None
        and "person_id" in target
        and target["person_id"] != subject_id
    ):
        return None
    return target if target else None


def matches(expected_value, observed):
    if not expected_value or not isinstance(observed, dict):
        return False
    # Canonical JSON type equality: bool and number are distinct.
    import json

    return all(
        key in observed
        and json.dumps(observed[key], sort_keys=True, ensure_ascii=False)
        == json.dumps(value, sort_keys=True, ensure_ascii=False)
        for key, value in expected_value.items()
    )
