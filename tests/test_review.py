from test_core import client, create


def test_completion_is_manual_and_requires_readback_kind(client):
    case = create(client)
    case_id = case["id"]
    client.post(f"/api/cases/{case_id}/approve", json={"revision": 1})
    proof = {
        "revision": 1,
        "kind": "other",
        "reference": "target record 42",
        "observed": {"value": 1},
    }
    assert client.post(f"/api/cases/{case_id}/evidence", json=proof).status_code == 200
    assert (
        client.post(f"/api/cases/{case_id}/complete", json={"revision": 1}).status_code
        == 409
    )
    proof["kind"] = "independent_readback"
    proof["reference"] = "   "
    assert client.post(f"/api/cases/{case_id}/evidence", json=proof).status_code == 422
    proof["reference"] = "target record 42"
    assert client.post(f"/api/cases/{case_id}/evidence", json=proof).status_code == 200
    completed = client.post(
        f"/api/cases/{case_id}/complete", json={"revision": 1}
    ).json()
    assert completed["status"] == "COMPLETED"
    assert completed["completion_basis"] == "manual_attestation"


def test_rejects_ambiguous_or_unrepresentable_json(client):
    url = "/api/tools/T1/test"
    for body in (
        '{"nested":{"x":1,"x":2}}',
        '{"x":NaN}',
        '{"x":1e999}',
        '{"x":"\\ud800"}',
    ):
        assert (
            client.post(
                url, content=body, headers={"Content-Type": "application/json"}
            ).status_code
            == 422
        )
    assert (
        client.post(
            url,
            content='{"x":"' + "a" * 1_000_000 + '"}',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
