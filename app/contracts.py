"""Input contracts for the local preview tools.

Structured records reject unknown keys; intentionally dynamic fact dictionaries accept
JSON values. Monetary and measured decimal inputs are represented as strings.
"""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math

S = {"type": "string", "minLength": 1}
B = {"type": "boolean"}
I = {"type": "integer"}
D = {
    "type": "string",
    "format": "decimal",
    "pattern": r"^-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)$",
}
N = {"anyOf": [D, I]}
DAY = {"type": "string", "format": "date"}
DT = {"type": "string", "format": "date-time"}
LOCAL_DT = {"type": "string", "format": "local-date-time"}
# Arbitrary values are reserved for explicitly user-defined facts, not records.
JSON = {"format": "json-value"}


def obj(required="", optional="", **fields):
    names = (required + " " + optional).split()
    props = {}
    for name in names:
        key, _, kind = name.partition(":")
        props[key] = deepcopy(fields.get(key, TYPES.get(kind, S)))
    return {
        "type": "object",
        "properties": props,
        "required": [x.split(":")[0] for x in required.split()],
        "additionalProperties": False,
    }


def arr(item):
    return {"type": "array", "items": item}


def mapping(item=JSON):
    return {"type": "object", "additionalProperties": item}


TYPES = {
    "s": S,
    "b": B,
    "i": I,
    "d": D,
    "n": N,
    "date": DAY,
    "dt": DT,
    "localdt": LOCAL_DT,
    "strings": arr(S),
    "map": mapping(),
    "strmap": mapping(S),
}
APP = obj("", "by scope_hash")
PERIOD = obj("start:date end:date")
PRED = obj("field op", "value", value=JSON)
FACT = obj("value source", "confirmed:b current:b", value=JSON)
SCHEMAS = {}


def add(ids, required, optional="", **fields):
    for id in ids.split():
        SCHEMAS[id] = obj(required, optional, **fields)


add("P01", "person_id old:d new:d unit basis valid_from:date", "approval", approval=APP)
add(
    "P02",
    "person_id old:d new:d unit model valid_from:date",
    "valid_to:date approval",
    approval=APP,
)
add(
    "P03",
    "round_id revision valid_from:date currency basis rule_version mode people",
    "percentage:d",
    revision={"anyOf": [S, I]},
    people=arr(obj("person_id old:d current:d", "new:d approval", approval=APP)),
)
add(
    "P04",
    "person_id fact_id old new valid_from:date reason history",
    "valid_to:date approval",
    history=arr(obj("value", value=JSON)),
    approval=APP,
    old=JSON,
    new=JSON,
)
add("P05 P12", "template template_version template_approved:b fields:map")
add(
    "P06",
    "document_hash version person_id return_evidence",
    return_evidence=obj("document_hash version person_id method", "evidence_id"),
)
add(
    "P07",
    "person_id measure draft rule_version representative consultation_scope consultation_evidence",
    consultation_evidence=obj("", "representative status scope_hash by measure_hash"),
)
add("P08", "person_id periods evidence", periods=arr(PERIOD))
add("P09", "person_id periods evidence previous_version decision", periods=arr(PERIOD))
add(
    "P10",
    "person_id return_date:date hours:d role leave_periods approval",
    "max_hours:d",
    leave_periods=arr(PERIOD),
    approval=APP,
)
add("P11", "person_id field old new evidence effective_date:date", old=JSON, new=JSON)
add(
    "P14",
    "person_id qualification evidence valid_until:date confirmed_by rule_version as_of:date",
)
add(
    "P15",
    "person_id end_date:date departure_type decision_evidence tasks",
    decision_evidence=obj("", "by evidence_id scope_hash"),
    tasks=arr(obj("name", "confirmed:b confirmed_by evidence_id")),
)
add("P16", "person_id absence_type start:date end:date approval handover", approval=APP)
add(
    "P17",
    "person_id documents",
    documents=arr(
        obj(
            "version content",
            "signature_evidence",
            signature_evidence=obj("", "document_hash version method evidence_id"),
        )
    ),
)
add(
    "P18",
    "case_type decision_fields:map revision role delegation valid_from:date valid_to:date",
    "approval",
    revision={"anyOf": [S, I]},
    approval=APP,
)
add(
    "A01",
    "branch cost_center owner role requirements:strings reason start:date end:date hours:d shift supplier",
    "approval",
    approval=APP,
)
add(
    "A02",
    "request_revision offers",
    offers=arr(
        obj("id supplier candidate start:date end:date hours:d rate:d extra_cost:d")
    ),
)
add(
    "A03",
    "offer_id offer_revision selection_evidence supplier candidate location role start:date end:date hours:d rate:d rules_version",
    "max_hours:d max_rate:d approval",
    approval=APP,
)
add(
    "A04",
    "order_revision start:date end:date requirements:strings documents",
    documents=arr(obj("type order_revision valid_from:date valid_until:date")),
)
add(
    "A05",
    "person_id start:date end:date supplier_lines time_lines",
    supplier_lines=arr(obj("id date:date hours:d approved:b")),
    time_lines=arr(obj("id date:date hours:d")),
)
add(
    "A06",
    "supplier invoice_number order_revision invoice_lines confirmed_lines existing_invoices",
    invoice_lines=arr(obj("id hours:d rate:d amount:d")),
    confirmed_lines=arr(obj("id hours:d rate:d")),
    existing_invoices=arr(obj("supplier invoice_number")),
)
add(
    "A07",
    "dispute_id reason line_ids:strings invoice_number correction_route recipient status",
    "resolution_evidence",
)
add(
    "A08",
    "order_revision action current_start:date current_end:date reason open_items",
    "new_end:date approval",
    open_items=arr(obj("name", "confirmed:b")),
    approval=APP,
)

attachment = {"anyOf": [S, obj("name sha256")]}
message = obj(
    "id sender subject body",
    "reference personal_data:b action_required:b attachments type status kind result error:b ndr:b",
    attachments=arr(attachment),
)
add(
    "M01", "message rules", message=message, rules=arr(obj("sender version approved:b"))
)
add(
    "M02",
    "message receipt retention",
    message=obj(
        "id hash", "reference type status kind subject body result error:b ndr:b"
    ),
    receipt=obj("result verified:b target timestamp"),
    retention=obj("approved:b version"),
)
add(
    "M03",
    "messages",
    messages=arr(
        obj(
            "id mailbox body",
            "internet_id attachment_hashes:strings questions:strings recipients:strings",
            internet_id={"anyOf": [S, {"type": "null"}]},
        )
    ),
)
add(
    "M04", "message role_mapping", message=obj("text"), role_mapping=obj("valid:b role")
)
add(
    "M05",
    "case_id questions answers",
    questions=arr(obj("id text", "recipient audience")),
    answers=arr(
        obj(
            "question_id case_id source state",
            "value direction recipient identity_confirmed:b delivery_evidence",
            value=JSON,
            delivery_evidence=obj("source delivered:b"),
        )
    ),
)
add(
    "M06",
    "source speaker message_date:date days:i fulfillment today:date",
    "condition evidence",
    evidence=obj("source fulfillment verified:b"),
)
add(
    "M07",
    "template facts",
    "recipients:strings",
    template=obj("text version", "approved:b"),
    facts=mapping(FACT),
)
add(
    "M08",
    "snapshot_hash current_snapshot",
    current_snapshot=obj(
        "template facts",
        "recipients:strings",
        template=obj("", "text version approved:b"),
        facts=mapping(FACT),
    ),
)
add(
    "M09",
    "task_id requester revision",
    "claim notes:strings",
    claim=obj("", "active:b owner"),
)
add(
    "M10",
    "records search_type query authorized_scopes:strings purpose",
    records=arr(obj("scope", "message_id case_id personnel_number name")),
)
add(
    "M11",
    "old:map new:map identity_confirmed:b case_id document_type",
    "dependencies",
    dependencies=arr(obj("fields:strings", "name id")),
)
add("M12", "cases authorized_scopes:strings", cases=arr(obj("person_id case_id scope")))
add(
    "M13",
    "tasks today:date rule_version",
    tasks=arr(obj("id status", "due:date deadline_approved:b blocked_steps:i")),
)
add(
    "M14",
    "absence tasks",
    absence=obj("start:date end:date deputy", "confirmed:b"),
    tasks=arr(obj("id", "due:date next_action source sensitive:b state")),
)
add(
    "M15",
    "content source owner version scope valid_from:date",
    "approved:b dependent_drafts:strings",
)

add(
    "R01",
    "branch role requested:d capacity:d occupied:d source requester_authorized:b",
    "approval_evidence",
)
add(
    "R02",
    "position channel text budget:d committed:d spent:d price:d approval",
    "drift:b",
)
add(
    "R03",
    "application_id received_at:dt channel",
    "message eml",
    message=obj(
        "",
        "subject body message_id from attachments",
        attachments=arr(obj("name hash")),
    ),
)
add("R04", "fields required:strings", fields=mapping(FACT))
add(
    "R05",
    "application_id identifiers:strmap candidates",
    "identity_evidence person_confirmation",
    candidates=arr(obj("person_id identifiers:strmap")),
)
allowed = obj("", "name email phone location")
add(
    "R06",
    "approved_fields existing_records identifier action source_id",
    "decision observed_fields readback readback_evidence",
    approved_fields=allowed,
    observed_fields=allowed,
    readback=allowed,
    decision=APP,
    existing_records=arr(obj("identifier")),
)
add(
    "R07",
    "case_id required_fields:strings answers template",
    answers=arr(obj("case_id field source complete:b")),
)
add(
    "R08",
    "submissions",
    submissions=arr(obj("agency message_id profile_hash received_at:dt")),
)
add(
    "R09",
    "application_id position_branch role_mapping fields purpose",
    role_mapping=obj("branch valid:b address"),
    fields=mapping(FACT),
)
add(
    "R10",
    "application_id recipients start:dt end:dt busy",
    "candidate_confirmed:b branch_confirmed:b",
    recipients=arr(obj("role address verified:b application_id")),
    busy=arr(obj("start:dt end:dt")),
)
add(
    "R11",
    "application_id feedback decision",
    decision=obj("state", "authorized_person source revision"),
)
add(
    "R12",
    "application_id purpose authorized:b facts",
    "open_questions:strings",
    facts=arr(obj("value source confirmed:b", value=JSON)),
)
add(
    "R13",
    "revision decision_evidence checklist",
    "hr_confirmation:b",
    checklist=mapping(obj("", "confirmed:b evidence revision")),
)
add(
    "R14",
    "old_date:date new_date:date source dependencies",
    "approval_evidence candidate_consent",
    dependencies=arr(obj("kind date_dependent:b")),
)
add(
    "R15",
    "old new authorized:b purpose identity_confirmed:b retention_valid:b",
    old=mapping(FACT),
    new=mapping(FACT),
)

add(
    "O01",
    "event rule",
    "existing_keys:strings",
    event=obj(
        "event_id revision type person_id date:date source",
        "ambiguous:b",
        revision={"anyOf": [S, I]},
    ),
    rule=obj(
        "id version status trigger steps",
        steps=arr(obj("id owner lead_days:i", "depends_on:strings")),
    ),
)
add(
    "O02",
    "target_date:date tasks",
    tasks=arr(obj("id duration_days:i", "depends_on:strings confirmed:b")),
)
add(
    "O03",
    "needs sources",
    "facts:map",
    needs=arr(obj("field purpose")),
    sources=arr(obj("field name allowed:b proven:b")),
)
add(
    "O04",
    "fields facts:map",
    fields=arr(obj("name", "when", when=obj("field equals", equals=JSON))),
)
add("O05", "changed:strings dependencies", dependencies=mapping(arr(S)))
add("O06", "decisions", decisions=arr(obj("id owner topic", "impact")))
add("O07", "scenarios", scenarios=arr(obj("name cost:n days:n")))
add(
    "O08",
    "date:date scope delegations",
    delegations=arr(obj("delegate scope from:date to:date approved:b")),
)
add(
    "O09",
    "tasks",
    tasks=arr(obj("id status", "depends_on:strings blocker owner next_step")),
)
add("O10", "questions answers:map", questions=arr(obj("field recipient")))
add(
    "O11",
    "corrections",
    corrections=arr(obj("field from to confirmed:b", **{"from": JSON, "to": JSON})),
)
add("O12", "rule cases", rule=PRED, cases=arr(mapping()))
add(
    "O13",
    "commitments",
    commitments=arr(obj("id", "owner due:date conditions_met:b proof")),
)
add("O14", "cases", cases=arr(obj("status", "duration_days:n rework:b cause")))
add(
    "T01",
    "valid_at:date known_at:date facts",
    facts=arr(
        obj(
            "field value valid_from:date observed_at:date source",
            "valid_to:date",
            value=JSON,
        )
    ),
)
add(
    "T02",
    "rule facts:map action scope object_id revision valid_from:date valid_to:date as_of:date required_role",
    "approval",
    revision={"anyOf": [S, I]},
    approval=APP,
    rule=obj("id version status predicate", predicate=PRED),
)
add("T03", "now:localdt timer_at:localdt", "lease_until:localdt external_state")
add(
    "T04",
    "capabilities",
    capabilities=arr(
        obj("system action scope", "approved_scope:b probe_passed:b evidence")
    ),
)
add(
    "T05",
    "case_id step revision target payload:map rule_version valid_from:date valid_to:date as_of:date required_role",
    "approval external_state",
    revision={"anyOf": [S, I]},
    approval=APP,
)
add(
    "T06",
    "expected:map observed:map evidence",
    evidence=obj("", "source independent:b reference"),
)
add("T07", "template version approved:b allowed_fields:strings facts:map")
add("T08", "text fields:strings")
add(
    "T09",
    "scope action policy records as_of:date",
    policy=obj("approved:b scopes:strings actions:strings"),
    records=arr(obj("id", "expires:date hold:b")),
)
add("T10", "contents:strmap manifest:strmap")
add("T11", "tests approval:b", tests=arr(obj("name result")))
add("T12", "tools", tools=arr(obj("id implemented:b tested:b")))

# Domain-specific numeric and size limits follow the underlying implementation.
SCHEMAS["T08"]["properties"]["text"]["maxLength"] = 100000
SCHEMAS["T08"]["properties"]["fields"]["maxItems"] = 50


def _validate(schema, value, path, depth=0):
    if depth > 32:
        raise ValueError(f"{path}: nesting is too deep")
    if "anyOf" in schema:
        for choice in schema["anyOf"]:
            try:
                return _validate(choice, value, path, depth)
            except ValueError:
                pass
        raise ValueError(f"{path}: invalid type or value")
    if schema.get("format") == "json-value":
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, str):
            if len(value) > 1000000:
                raise ValueError(f"{path}: string too long")
            return value
        if isinstance(value, float):
            if math.isfinite(value):
                return value
            raise ValueError(f"{path}: non-finite number")
        if isinstance(value, list):
            if len(value) > 10000:
                raise ValueError(f"{path}: too many items")
            return [
                _validate(JSON, v, f"{path}[{i}]", depth + 1)
                for i, v in enumerate(value)
            ]
        if isinstance(value, dict):
            if len(value) > 10000:
                raise ValueError(f"{path}: too many fields")
            if not all(isinstance(k, str) and len(k) <= 1000 for k in value):
                raise ValueError(
                    f"{path}: keys must be strings of at most 1000 characters"
                )
            return {
                k: _validate(JSON, v, f"{path}.{k}", depth + 1)
                for k, v in value.items()
            }
        raise ValueError(f"{path}: expected JSON value")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: invalid choice")
    typ = schema.get("type")
    if typ == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected object")
        if len(value) > 10000:
            raise ValueError(f"{path}: too many fields")
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ValueError(f"{path}.{key}: required")
        out = {}
        for key, v in value.items():
            if not isinstance(key, str) or len(key) > 1000:
                raise ValueError(
                    f"{path}: keys must be strings of at most 1000 characters"
                )
            sub = props.get(key, schema.get("additionalProperties", False))
            if sub is False:
                raise ValueError(f"{path}.{key}: unknown field")
            out[key] = _validate(sub, v, f"{path}.{key}", depth + 1)
        return out
    if typ == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected array")
        if len(value) > schema.get("maxItems", 10000):
            raise ValueError(f"{path}: too many items")
        return [
            _validate(schema["items"], v, f"{path}[{i}]", depth + 1)
            for i, v in enumerate(value)
        ]
    if typ == "null":
        if value is not None:
            raise ValueError(f"{path}: expected null")
    elif typ == "boolean":
        if type(value) is not bool:
            raise ValueError(f"{path}: expected boolean")
    elif typ == "integer":
        if type(value) is not int:
            raise ValueError(f"{path}: expected integer")
    elif typ == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path}: expected string")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get(
            "maxLength", 1000000
        ):
            raise ValueError(f"{path}: invalid length")
        fmt = schema.get("format")
        try:
            if fmt == "decimal":
                import re

                if (
                    not re.fullmatch(schema["pattern"], value)
                    or not Decimal(value).is_finite()
                ):
                    raise ValueError()
            elif fmt == "date":
                if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            elif fmt in ("date-time", "local-date-time"):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if fmt == "date-time" and dt.utcoffset() is None:
                    raise ValueError()
        except (ValueError, InvalidOperation, OverflowError):
            raise ValueError(f"{path}: invalid {fmt}") from None
    return deepcopy(value)


def input_schema(tool_id):
    if tool_id not in SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_id}")
    schema = deepcopy(SCHEMAS[tool_id])

    def label(s):
        for key, child in s.get("properties", {}).items():
            child.setdefault("title", key.replace("_", " ").capitalize())
            label(child)
        if isinstance(s.get("items"), dict):
            label(s["items"])
        if isinstance(s.get("additionalProperties"), dict):
            label(s["additionalProperties"])

    label(schema)
    schema["title"] = tool_id
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def validate_payload(tool_id, payload):
    if tool_id not in SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_id}")
    result = _validate(SCHEMAS[tool_id], payload, "$")
    if tool_id == "T03":
        timestamps = [
            datetime.fromisoformat(result[k].replace("Z", "+00:00"))
            for k in ("now", "timer_at", "lease_until")
            if k in result
        ]
        if len({x.utcoffset() is None for x in timestamps}) > 1:
            raise ValueError("$.now: timestamps must use consistent timezone awareness")
    if tool_id in ("T02", "T05", "O01"):
        revision = (
            result["event"]["revision"] if tool_id == "O01" else result["revision"]
        )
        if type(revision) is int and revision <= 0:
            raise ValueError("$.revision: must be positive")
    if tool_id == "R06" and result["action"] not in ("create", "update"):
        raise ValueError("$.action: expected create or update")
    if tool_id == "P02":
        for field in ("old", "new"):
            if not 0 < Decimal(result[field]) <= 168:
                raise ValueError(f"$.{field}: must be greater than 0 and at most 168")
    for field in {
        "P01": ("old", "new"),
        "A01": ("hours",),
        "A03": ("hours", "rate"),
        "R01": ("requested", "capacity", "occupied"),
        "R02": ("budget", "committed", "spent", "price"),
    }.get(tool_id, ()):
        if Decimal(result[field]) < 0:
            raise ValueError(f"$.{field}: must be nonnegative")
    if tool_id == "O14":
        for i, case in enumerate(result["cases"]):
            if case["status"] not in ("open", "closed"):
                raise ValueError(f"$.cases[{i}].status: expected open or closed")
            if "duration_days" in case and (
                case["status"] != "closed" or Decimal(case["duration_days"]) < 0
            ):
                raise ValueError(
                    f"$.cases[{i}].duration_days: requires a closed case and a nonnegative value"
                )
    if tool_id == "R06" and not result["approved_fields"]:
        raise ValueError("$.approved_fields: at least one field required")
    if tool_id == "R03" and not (result.get("message") or result.get("eml")):
        raise ValueError("$.message: message or eml required")
    if (
        tool_id == "P03"
        and result["mode"] == "percentage"
        and "percentage" not in result
    ):
        raise ValueError("$.percentage: required for percentage mode")
    if tool_id == "P03" and result["mode"] == "manual":
        for i, person in enumerate(result["people"]):
            if "new" not in person:
                raise ValueError(f"$.people[{i}].new: required for manual mode")
    if tool_id == "P02" and result["model"] == "befristet" and "valid_to" not in result:
        raise ValueError("$.valid_to: required for befristet")
    if tool_id == "A08" and result["action"] == "extend" and "new_end" not in result:
        raise ValueError("$.new_end: required for extend")
    return result
