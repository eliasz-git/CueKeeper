import importlib
import json

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as WSTestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CUEKEEPER_DATA", str(tmp_path / "data.json"))
    monkeypatch.setenv("CUEKEEPER_AUDIO", str(tmp_path / "audio"))
    monkeypatch.setenv("CUEKEEPER_AUTH_REQUIRED", "false")
    import src.main

    main = importlib.reload(src.main)
    with TestClient(main.app) as c:
        c.tmp_path = tmp_path
        yield c


def upload(client, name, filename, content=b"RIFF fake audio"):
    return client.post(
        "/api/cues", data={"name": name}, files={"file": (filename, content)}
    )


def test_startup_creates_data_and_audio(client):
    assert json.loads((client.tmp_path / "data.json").read_text()) == {
        "cues": [],
        "next_id": 1,
    }
    assert (client.tmp_path / "audio").is_dir()


def test_list_starts_empty(client):
    assert client.get("/api/cues").json() == []


def test_upload_creates_cue_and_file(client):
    r = upload(client, "Thunder", "thunder.mp3")
    assert r.status_code == 201
    assert r.json() == {"id": 1, "name": "Thunder", "file": "thunder.mp3"}
    assert (
        client.tmp_path / "audio" / "thunder.mp3"
    ).read_bytes() == b"RIFF fake audio"
    assert client.get("/api/cues").json() == [r.json()]


def test_uploaded_audio_is_served(client):
    upload(client, "Thunder", "thunder.mp3")
    r = client.get("/audio/thunder.mp3")
    assert r.status_code == 200
    assert r.content == b"RIFF fake audio"


def test_ids_are_sequential(client):
    ids = [upload(client, f"Cue {i}", f"c{i}.wav").json()["id"] for i in range(3)]
    assert ids == [1, 2, 3]


def test_same_filename_does_not_overwrite(client):
    upload(client, "One", "door.wav", b"one")
    second = upload(client, "Two", "door.wav", b"two").json()
    assert second["file"] == "door-1.wav"
    assert (client.tmp_path / "audio" / "door.wav").read_bytes() == b"one"
    assert (client.tmp_path / "audio" / "door-1.wav").read_bytes() == b"two"


def test_path_traversal_is_stripped(client):
    r = upload(client, "Sneaky", "../../evil.mp3")
    assert r.status_code == 201
    assert r.json()["file"] == "evil.mp3"
    assert not (client.tmp_path / "evil.mp3").exists()
    assert (client.tmp_path / "audio" / "evil.mp3").exists()


@pytest.mark.parametrize("filename", ["notes.txt", "script.py", "noext"])
def test_rejects_non_audio(client, filename):
    assert upload(client, "Bad", filename).status_code == 400
    assert client.get("/api/cues").json() == []


def test_rejects_blank_name(client):
    assert upload(client, "   ", "a.mp3").status_code == 400


def test_hello_route_is_reachable(client):
    assert client.get("/hello").json() == {"message": "hello"}


def test_index_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "CueKeeper" in r.text


def test_delete_cue(client):
    upload(client, "Thunder", "thunder.mp3")
    r = client.delete("/api/cues/1")
    assert r.status_code == 204
    assert client.get("/api/cues").json() == []


def test_delete_missing_cue(client):
    r = client.delete("/api/cues/999")
    assert r.status_code == 404


def test_trigger_cue(client):
    upload(client, "Thunder", "thunder.mp3")
    r = client.post("/api/cues/1/trigger")
    assert r.status_code == 200
    assert r.json()["status"] == "triggered"
    assert r.json()["cue"]["id"] == 1


def test_trigger_missing_cue(client):
    r = client.post("/api/cues/999/trigger")
    assert r.status_code == 404


def test_websocket_connects(client):
    import src.main

    main = importlib.reload(src.main)
    with WSTestClient(main.app) as c, c.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        # Connection stays open; no echo expected from server


@pytest.fixture
def authed_client(tmp_path, monkeypatch):
    """Test client with CUEKEEPER_TOKEN enabled."""
    monkeypatch.setenv("CUEKEEPER_DATA", str(tmp_path / "data.json"))
    monkeypatch.setenv("CUEKEEPER_AUDIO", str(tmp_path / "audio"))
    monkeypatch.setenv("CUEKEEPER_TOKEN", "secret-token-123")
    import src.main

    main = importlib.reload(src.main)
    with TestClient(main.app) as c:
        c.tmp_path = tmp_path
        yield c


def authed_upload(client, name, filename, content=b"RIFF fake audio"):
    return client.post(
        "/api/cues",
        data={"name": name},
        files={"file": (filename, content)},
        headers={"Authorization": "Bearer secret-token-123"},
    )


def test_authed_upload_without_token_returns_401(authed_client):
    r = authed_client.post(
        "/api/cues", data={"name": "X"}, files={"file": ("x.mp3", b"data")}
    )
    assert r.status_code == 401


def test_authed_upload_with_wrong_token_returns_401(authed_client):
    r = authed_client.post(
        "/api/cues",
        data={"name": "X"},
        files={"file": ("x.mp3", b"data")},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_authed_upload_with_valid_token_succeeds(authed_client):
    r = authed_upload(authed_client, "Thunder", "thunder.mp3")
    assert r.status_code == 201
    assert r.json() == {"id": 1, "name": "Thunder", "file": "thunder.mp3"}


def test_authed_delete_without_token_returns_401(authed_client):
    r = authed_client.delete("/api/cues/1")
    assert r.status_code == 401


def test_authed_delete_with_valid_token_succeeds(authed_client):
    authed_upload(authed_client, "Thunder", "thunder.mp3")
    r = authed_client.delete(
        "/api/cues/1", headers={"Authorization": "Bearer secret-token-123"}
    )
    assert r.status_code == 204


def test_authed_trigger_without_token_returns_401(authed_client):
    r = authed_client.post("/api/cues/1/trigger")
    assert r.status_code == 401


def test_authed_trigger_with_valid_token_succeeds(authed_client):
    authed_upload(authed_client, "Thunder", "thunder.mp3")
    r = authed_client.post(
        "/api/cues/1/trigger", headers={"Authorization": "Bearer secret-token-123"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "triggered"


def test_websocket_rejects_invalid_token(authed_client):
    import src.main

    main = importlib.reload(src.main)
    with (
        WSTestClient(main.app) as c,
        c.websocket_connect("/ws?token=wrong") as ws,
        pytest.raises(WebSocketDisconnect),
    ):
        ws.receive_text()


def test_websocket_accepts_valid_token(authed_client):
    import src.main

    main = importlib.reload(src.main)
    with (
        WSTestClient(main.app) as c,
        c.websocket_connect("/ws?token=secret-token-123") as ws,
    ):
        ws.send_text("ping")


@pytest.fixture
def strict_rate_client(tmp_path, monkeypatch):
    """Test client with a very low rate limit (3 requests per path per window)."""
    monkeypatch.setenv("CUEKEEPER_DATA", str(tmp_path / "data.json"))
    monkeypatch.setenv("CUEKEEPER_AUDIO", str(tmp_path / "audio"))
    monkeypatch.setenv("CUEKEEPER_TOKEN", "")
    monkeypatch.setenv("CUEKEEPER_AUTH_REQUIRED", "false")
    monkeypatch.setenv("CUEKEEPER_RATE_LIMIT_REQUESTS", "3")
    monkeypatch.setenv("CUEKEEPER_RATE_LIMIT_WINDOW", "60")
    import src.main

    main = importlib.reload(src.main)
    with TestClient(main.app) as c:
        c.tmp_path = tmp_path
        yield c


def test_ids_never_reuse_after_delete(client):
    """Deleted cue IDs must never be reused (monotonic counter)."""
    upload(client, "One", "one.mp3")
    upload(client, "Two", "two.mp3")
    client.delete("/api/cues/1")
    r = upload(client, "Three", "three.mp3")
    assert r.status_code == 201
    assert r.json()["id"] == 3  # not 1 — IDs never reuse


def test_rate_limiting_returns_429(strict_rate_client):
    """Exceeding the rate limit returns HTTP 429."""
    # First 3 requests should succeed
    for _ in range(3):
        r = strict_rate_client.get("/api/cues")
        assert r.status_code == 200
    # 4th request should be rate limited
    r = strict_rate_client.get("/api/cues")
    assert r.status_code == 429


def test_security_headers_present(client):
    r = client.get("/api/cues")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "same-origin"


def test_cors_headers_present(client):
    r = client.options("/api/cues", headers={"Origin": "http://localhost:3000"})
    assert r.headers["Access-Control-Allow-Origin"] == "*"


@pytest.fixture
def noauth_client(tmp_path, monkeypatch):
    """Client with auth required (default) but no token configured -> fail-closed."""
    monkeypatch.setenv("CUEKEEPER_DATA", str(tmp_path / "data.json"))
    monkeypatch.setenv("CUEKEEPER_AUDIO", str(tmp_path / "audio"))
    # CUEKEEPER_TOKEN unset, CUEKEEPER_AUTH_REQUIRED defaults to "true"
    import src.main

    main = importlib.reload(src.main)
    with TestClient(main.app) as c:
        c.tmp_path = tmp_path
        yield c


def test_auth_required_returns_503_when_no_token(noauth_client):
    """Fail-closed: mutating without a configured token returns 503, not 201."""
    r = noauth_client.post(
        "/api/cues", data={"name": "X"}, files={"file": ("x.mp3", b"data")}
    )
    assert r.status_code == 503


def test_get_cues_requires_auth_when_token_configured(authed_client):
    """GET /api/cues is protected when a token is configured."""
    r = authed_client.get("/api/cues")
    assert r.status_code == 401


def test_401_includes_www_authenticate(authed_client):
    r = authed_client.post("/api/cues/1/trigger")
    assert r.status_code == 401
    assert "Bearer" in r.headers.get("WWW-Authenticate", "")


def test_429_includes_retry_after(strict_rate_client):
    for _ in range(3):
        strict_rate_client.get("/api/cues")
    r = strict_rate_client.get("/api/cues")
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_csp_header_present(client):
    r = client.get("/")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp


def test_healthz_endpoint(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
