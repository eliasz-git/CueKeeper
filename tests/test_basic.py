import importlib
import json

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as WSTestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CUEKEEPER_DATA", str(tmp_path / "data.json"))
    monkeypatch.setenv("CUEKEEPER_AUDIO", str(tmp_path / "audio"))
    import src.main

    main = importlib.reload(src.main)
    with TestClient(main.app) as c:
        c.tmp_path = tmp_path
        yield c


def upload(client, name, filename, content=b"RIFF fake audio"):
    return client.post("/api/cues", data={"name": name}, files={"file": (filename, content)})


def test_startup_creates_data_and_audio(client):
    assert json.loads((client.tmp_path / "data.json").read_text()) == {"cues": []}
    assert (client.tmp_path / "audio").is_dir()


def test_list_starts_empty(client):
    assert client.get("/api/cues").json() == []


def test_upload_creates_cue_and_file(client):
    r = upload(client, "Thunder", "thunder.mp3")
    assert r.status_code == 201
    assert r.json() == {"id": 1, "name": "Thunder", "file": "thunder.mp3"}
    assert (client.tmp_path / "audio" / "thunder.mp3").read_bytes() == b"RIFF fake audio"
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
    with WSTestClient(main.app).websocket_connect("/ws") as ws:
        ws.send_text("ping")
        # Connection stays open; no echo expected from server
