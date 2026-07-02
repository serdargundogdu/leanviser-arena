"""HTTP API: scenario descriptor and the simulate endpoint (end-to-end)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_scenario() -> None:
    response = client.get("/api/scenario")
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "baseline"
    assert body["takt_time"] > 0
    keys = {lever["key"] for lever in body["levers"]}
    assert keys == {"batch_size", "release_interval", "variance_factor"}


def test_post_simulate_with_defaults() -> None:
    response = client.post("/api/simulate", json={"batch_size": 5, "release_interval": 0.0})
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["score"]["composite"] <= 100.0
    assert len(body["lead_times"]) == body["metrics"]["order_count"]
    assert len(body["on_time"]) == body["metrics"]["order_count"]


def test_lean_flow_scores_higher_via_api() -> None:
    lean = client.post("/api/simulate", json={"batch_size": 1, "release_interval": 6.0}).json()
    push = client.post("/api/simulate", json={"batch_size": 5, "release_interval": 0.0}).json()
    assert lean["score"]["composite"] > push["score"]["composite"]


def test_simulate_is_deterministic() -> None:
    body = {"batch_size": 2, "release_interval": 4.0}
    first = client.post("/api/simulate", json=body).json()
    second = client.post("/api/simulate", json=body).json()
    assert first == second
