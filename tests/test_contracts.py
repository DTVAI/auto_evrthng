from copy import deepcopy
import pytest
from app.contracts import input_schema, validate_payload
from app.registry import catalog, tool_definition
from app.domains import (
    communication,
    recruiting,
    personnel,
    staffing,
    orchestration,
    platform,
)

DOMAINS = (communication, recruiting, personnel, staffing, orchestration, platform)
# Reviewed outcomes of the synthetic examples, deliberately independent of the registry.
EXPECTED = {
    **{f"M{i:02}": "READY" for i in range(1, 16)},
    **{f"R{i:02}": "READY" for i in range(1, 16)},
    **dict(
        zip(
            (
                "P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P14 P15 P16 P17 P18"
            ).split(),
            (
                "NEEDS_DECISION NEEDS_DECISION NEEDS_DECISION NEEDS_DECISION READY NEEDS_DECISION READY READY READY NEEDS_DECISION READY READY READY NEEDS_DECISION NEEDS_DECISION READY NEEDS_DECISION"
            ).split(),
        )
    ),
    **dict(
        zip(
            (f"A{i:02}" for i in range(1, 9)),
            (
                "NEEDS_DECISION READY NEEDS_DECISION READY READY READY NEEDS_DECISION NEEDS_DECISION"
            ).split(),
        )
    ),
    **dict(
        zip(
            (f"O{i:02}" for i in range(1, 15)),
            (
                "READY NEEDS_DECISION NEEDS_DATA NEEDS_DATA READY NEEDS_DECISION NEEDS_DECISION READY NEEDS_DATA NEEDS_DATA NEEDS_DECISION READY READY READY"
            ).split(),
        )
    ),
    **dict(
        zip(
            (f"T{i:02}" for i in range(1, 13)),
            (
                "READY READY NEEDS_DECISION READY READY READY READY NEEDS_DECISION READY READY READY READY"
            ).split(),
        )
    ),
}
SAMPLES = {k: (m, v) for m in DOMAINS for k, v in m.SAMPLES.items()}


@pytest.mark.parametrize("tool_id", sorted(EXPECTED))
def test_sample_contract_and_independent_status(tool_id):
    module, sample = SAMPLES[tool_id]
    assert validate_payload(tool_id, sample) == sample
    assert module.run(tool_id, deepcopy(sample))["status"] == EXPECTED[tool_id]
    definition = tool_definition(tool_id)
    assert definition["help"]["sample_input"] == sample
    assert definition["help"]["sample_status"] == EXPECTED[tool_id]
    schema = input_schema(tool_id)
    assert schema["type"] == "object" and schema["properties"] and schema["required"]
    missing = deepcopy(sample)
    del missing[schema["required"][0]]
    with pytest.raises(ValueError, match="required"):
        validate_payload(tool_id, missing)
    malformed = deepcopy(sample)
    malformed[schema["required"][0]] = None
    with pytest.raises(ValueError, match=schema["required"][0]):
        validate_payload(tool_id, malformed)
    with pytest.raises(ValueError, match="unknown field"):
        validate_payload(tool_id, {**sample, "unknown_field": True})
    with pytest.raises(ValueError, match="expected object"):
        validate_payload(tool_id, [])


def test_registry_covers_all_active_tools():
    assert len(catalog()) == len(EXPECTED) == len(SAMPLES) == 81
    assert {x["id"] for x in catalog()} == set(EXPECTED)


@pytest.mark.parametrize(
    "path,value",
    [("old", True), ("old", 1.5), ("old", "NaN"), ("valid_from", "2026-02-30")],
)
def test_decimal_and_date_errors(path, value):
    sample = deepcopy(SAMPLES["P01"][1])
    sample[path] = value
    with pytest.raises(ValueError, match=path):
        validate_payload("P01", sample)


def test_nested_types_and_sensitive_fields():
    sample = deepcopy(SAMPLES["A06"][1])
    sample["invoice_lines"][0]["amount"] = False
    with pytest.raises(ValueError, match=r"invoice_lines\[0\]\.amount"):
        validate_payload("A06", sample)
    sample = deepcopy(SAMPLES["R06"][1])
    sample["approved_fields"]["salary"] = "100"
    with pytest.raises(ValueError, match=r"approved_fields.salary"):
        validate_payload("R06", sample)


def test_empty_collections_and_aware_timestamps():
    sample = deepcopy(SAMPLES["A06"][1])
    sample["existing_invoices"] = []
    assert validate_payload("A06", sample)["existing_invoices"] == []
    sample = deepcopy(SAMPLES["R03"][1])
    sample["received_at"] = "2026-10-01T12:00:00"
    with pytest.raises(ValueError, match="received_at"):
        validate_payload("R03", sample)


def test_workflow_and_import_shapes_are_accepted():
    plan = deepcopy(SAMPLES["O02"][1])
    for task in plan["tasks"]:
        task["confirmed"] = True
    assert orchestration.run("O02", validate_payload("O02", plan))["status"] == "READY"
    event = deepcopy(SAMPLES["O01"][1])
    event["event"]["ambiguous"] = False
    event["rule"]["steps"][0]["depends_on"] = []
    first = orchestration.run("O01", validate_payload("O01", event))
    event["existing_keys"] = [first["data"]["tasks"][0]["key"]]
    assert orchestration.run("O01", validate_payload("O01", event))["data"]["tasks"][0][
        "existing"
    ]
    needs = deepcopy(SAMPLES["O03"][1])
    needs["facts"] = {"location": "Berlin"}
    assert orchestration.run("O03", validate_payload("O03", needs))["status"] == "READY"
    mail = deepcopy(SAMPLES["M01"][1])
    mail["message"]["attachments"] = [{"name": "cv.pdf", "sha256": "abc"}]
    assert (
        communication.run("M01", validate_payload("M01", mail))["status"]
        == "NEEDS_DECISION"
    )
    dedupe = deepcopy(SAMPLES["M03"][1])
    dedupe["messages"][0]["internet_id"] = None
    assert (
        communication.run("M03", validate_payload("M03", dedupe))["status"] == "READY"
    )
    mail["message"]["kind"] = "NDR"
    assert (
        communication.run("M01", validate_payload("M01", mail))["status"] == "EXCEPTION"
    )


def test_dynamic_facts_are_bounded_and_finite():
    sample = deepcopy(SAMPLES["T05"][1])
    sample["payload"] = {"value": float("inf")}
    with pytest.raises(ValueError, match=r"payload.value"):
        validate_payload("T05", sample)
    item = "x"
    for _ in range(35):
        item = {"child": item}
    sample["payload"] = {"value": item}
    with pytest.raises(ValueError, match="nesting is too deep"):
        validate_payload("T05", sample)
