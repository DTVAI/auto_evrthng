from test_core import client, create


def test_source_identity_and_title_history(client):
    first = client.post(
        "/api/tools/T1/cases",
        json={
            "title": "Old",
            "source_ref": " ref ",
            "subject_id": "A",
            "payload": {"x": 1},
        },
    ).json()
    assert (
        client.post(
            "/api/tools/T1/cases",
            json={
                "title": "Old",
                "source_ref": "ref",
                "subject_id": "B",
                "payload": {"x": 1},
            },
        ).status_code
        == 409
    )
    updated = client.patch(
        f"/api/cases/{first['id']}",
        json={"revision": 1, "title": "New", "payload": {"x": 1}},
    ).json()
    assert [r["title"] for r in updated["revisions"]] == ["Old", "New"]
    assert (
        client.post(
            "/api/tools/T1/cases",
            json={
                "title": "Old",
                "source_ref": "ref",
                "subject_id": "A",
                "payload": {"x": 1},
            },
        ).json()["id"]
        == first["id"]
    )
    assert updated["created_at"].endswith("+00:00") and updated["revisions"][0][
        "created_at"
    ].endswith("+00:00")


def test_limits_and_utc(client):
    assert (
        client.post(
            "/api/tools/T1/test",
            content=b"[" * 40 + b"0" + b"]" * 40,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/tools/T1/test",
            content=b" " * 1000001,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    job = client.post(
        "/api/jobs",
        json={"tool_id": "T1", "payload": {}, "due_at": "2030-01-01T12:00:00+02:00"},
    ).json()
    assert job["due_at"] == "2030-01-01T10:00:00+00:00"
    assert client.get("/api/jobs").json()[0]["due_at"] == job["due_at"]


def test_claim_scope(client):
    case = create(client)
    path = f"/api/cases/{case['id']}"
    assert (
        client.post(
            path + "/claim", json={"identity": "deputy", "deputy_for": "owner"}
        ).status_code
        == 200
    )
    assert client.post(path + "/claim", json={"identity": "other"}).status_code == 409
    assert len(client.get("/api/cases", params={"identity": "owner"}).json()) == 1
    assert client.post(path + "/release", json={"identity": "other"}).status_code == 409
    assert (
        client.post(
            path + "/release", json={"identity": "deputy", "deputy_for": "owner"}
        ).status_code
        == 200
    )


def test_stream_limit_stops_reading():
    import asyncio
    from app.main import app

    async def run():
        sent = []
        chunks = [b" " * 600000, b" " * 500000, b"never read"]
        reads = 0

        async def receive():
            nonlocal reads
            chunk = chunks[reads]
            reads += 1
            return {"type": "http.request", "body": chunk, "more_body": True}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/jobs",
            "raw_path": b"/api/jobs",
            "query_string": b"",
            "headers": [(b"host", b"localhost"), (b"x-toolbox-request", b"1")],
            "client": ("127.0.0.1", 1234),
            "server": ("localhost", 80),
        }
        await app(scope, receive, send)
        assert reads == 2
        assert (
            next(m for m in sent if m["type"] == "http.response.start")["status"] == 413
        )

    asyncio.run(run())


def test_nested_subject_mismatch_cannot_be_attested():
    from app.domains.orchestration import SAMPLES
    from app.projections import expected, matches

    assert expected("O01", SAMPLES["O01"], "DIFFERENT") is None
    assert not matches({}, {})
