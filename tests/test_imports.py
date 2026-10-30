import hashlib

from test_core import client


def upload(client, format, content, tool_id=None):
    return client.post(
        "/api/imports",
        json={
            "format": format,
            "content": content,
            "tool_id": tool_id,
            "filename": "input.txt",
        },
    )


def test_eml_import_is_a_preview_and_has_stable_source_hash(client):
    content = "From: person@example.org\nSubject: Bewerbung\nMessage-ID: <abc@example.org>\n\nHello"
    first = upload(client, "eml", content, "M01").json()
    second = upload(client, "eml", content, "M01").json()
    assert first == second
    assert (
        first["source_ref"] == "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    )
    assert first["tool_payload"]["message"]["sender"] == "person@example.org"
    assert first["tool_payload"]["rules"] == []
    assert "keine Befugnis" in first["warnings"][0]
    assert client.get("/api/cases").json() == []
    recruitment = upload(client, "eml", content, "R03").json()["tool_payload"]
    assert "received_at" not in recruitment
    assert upload(client, "eml", "Subject: missing sender\n\nText").status_code == 422


def test_csv_and_json_validation(client):
    result = upload(client, "csv", "name;role\nAda;HR\n").json()
    assert result["data"] == [{"name": "Ada", "role": "HR"}]
    for bad in ("name,name\nAda,HR\n", "name,role\nAda\n", 'name,role\n"Ada,HR\n'):
        assert upload(client, "csv", bad).status_code == 422
    for bad in ('{"x":1,"x":2}', '{"x":1e999}', '{"x":NaN}', "broken"):
        assert upload(client, "json", bad).status_code == 422
    assert upload(client, "json", '{"x":1}').json()["tool_payload"] == {"x": 1}


def test_import_hash_can_deduplicate_cases_but_grants_no_completion(client):
    imported = upload(client, "json", '{"value":1}').json()
    body = {
        "title": "Import",
        "payload": imported["tool_payload"],
        "source_ref": imported["source_ref"],
    }
    first = client.post("/api/tools/T1/cases", json=body).json()
    second = client.post("/api/tools/T1/cases", json=body).json()
    assert first["id"] == second["id"]
    assert first["approvals"] == [] and first["evidence"] == []
    assert (
        client.post(
            f"/api/cases/{first['id']}/complete", json={"revision": 1}
        ).status_code
        == 409
    )
