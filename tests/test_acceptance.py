"""Cross-package acceptance through the real API, with synthetic data only."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import services
from app.db import Base, get_db
from app.main import app


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'acceptance.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr("app.main.init_db", lambda: None)
    with TestClient(
        app, base_url="http://localhost", headers={"X-Toolbox-Request": "1"}
    ) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_every_active_catalog_tool_is_executable(api):
    tools = api.get("/api/tools").json()
    expected = {
        f"{prefix}{n:02d}"
        for prefix, count in [
            ("M", 15),
            ("R", 15),
            ("P", 18),
            ("A", 8),
            ("O", 14),
            ("T", 12),
        ]
        for n in range(1, count + 1)
    } - {"P13"}
    assert {tool["id"] for tool in tools} == expected
    for tool in tools:
        assert tool["implementation_status"] == "implemented", tool["id"]
        assert tool["sample"] and tool["goal"] and tool["steps"]
        response = api.post(f"/api/tools/{tool['id']}/test", json=tool["sample"])
        assert response.status_code == 200, (tool["id"], response.text)
        result = response.json()
        assert result["status"] != "EXCEPTION", (tool["id"], result)
        assert result["run_id"] > 0
        assert api.get(f"/api/runs/{result['run_id']}").status_code == 200
    assert api.get("/api/tools/P13").status_code == 404
    assert api.get("/api/dashboard").json()["test_runs"] == 81
    assert api.get("/api/integrations").json()["external_actions_enabled"] is False


def test_real_draft_artifact_and_versioned_case(api):
    sample = deepcopy(services.tool_info(services.tool("M07"))["sample"])
    sample["facts"]["name"]["value"] = "Mara Beispiel"
    created = api.post(
        "/api/tools/M07/cases",
        json={
            "title": "Antwortentwurf",
            "source_ref": "synthetic:m07",
            "subject_id": "P-DEMO",
            "payload": sample,
        },
    ).json()
    ident = created["id"]
    assert created["status"] == "OPEN"
    assert created["expected_observation"] == {"draft": "Guten Tag Mara Beispiel"}
    artifact = created["artifacts"][0]
    download = api.get(artifact["download_url"])
    assert "Mara Beispiel" in download.text
    assert "attachment" in download.headers["content-disposition"]
    assert (
        api.post(f"/api/cases/{ident}/complete", json={"revision": 1}).status_code
        == 409
    )
    api.post(
        f"/api/cases/{ident}/approve",
        json={"revision": 1, "comment": "Synthetischer Test"},
    )
    api.post(
        f"/api/cases/{ident}/evidence",
        json={
            "revision": 1,
            "kind": "independent_readback",
            "reference": "manuell:synthetischer-quellvergleich",
            "observed": sample,
        },
    )
    assert (
        api.post(f"/api/cases/{ident}/complete", json={"revision": 1}).status_code
        == 409
    )
    api.post(
        f"/api/cases/{ident}/evidence",
        json={
            "revision": 1,
            "kind": "independent_readback",
            "reference": "manuell:synthetischer-entwurfvergleich",
            "observed": {"draft": "Guten Tag Mara Beispiel"},
        },
    )
    done = api.post(f"/api/cases/{ident}/complete", json={"revision": 1})
    assert done.status_code == 200
    assert done.json()["completion_basis"] == "manual_attestation"
    sample["facts"]["name"]["value"] = "Alex Beispiel"
    changed = api.patch(f"/api/cases/{ident}", json={"revision": 1, "payload": sample})
    assert changed.json()["status"] == "OPEN"
    assert changed.json()["revision"] == 2
    assert (
        api.post(f"/api/cases/{ident}/complete", json={"revision": 2}).status_code
        == 409
    )
    assert "Mara Beispiel" in api.get(artifact["download_url"]).text
