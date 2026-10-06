import pytest
from fastapi.testclient import TestClient

import storage
from main import app

client = TestClient(app)

VALID = {
    "farm_id": "FARM-001", "region": "Krasnodar", "crop_type": "wheat",
    "area_ha": 2500, "temperature_avg": 24.3, "precipitation_mm": 320,
    "payment_delay_days": 45, "previous_defaults": 1, "debt": 6500000,
}


@pytest.fixture(autouse=True)
def _clean():
    storage.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert "x-process-time" in r.headers


def test_model_info():
    r = client.get("/model-info")
    assert r.status_code == 200
    assert r.json()["status"] == "ready" and r.json()["model_name"] == "agro-risk-model"


def test_predict_high_risk():
    r = client.post("/predict", json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["risk_score"] == 0.9 and body["risk_level"] == "high"


def test_predict_invalid_area_422():
    assert client.post("/predict", json={**VALID, "area_ha": -100}).status_code == 422


def test_predict_unknown_region_400():
    r = client.post("/predict", json={**VALID, "region": "Mars"})
    assert r.status_code == 400 and "Unknown region" in r.json()["detail"]


def test_predict_model_unavailable_503(monkeypatch):
    monkeypatch.setenv("MODEL_READY", "false")
    assert client.post("/predict", json=VALID).status_code == 503


def test_get_by_id_and_404():
    rid = client.post("/predict", json=VALID).json()["request_id"]
    assert client.get(f"/predictions/{rid}").status_code == 200
    assert client.get("/predictions/unknown").status_code == 404


def test_list_limit_filter_order():
    client.post("/predict", json={**VALID, "farm_id": "A"})  # high
    client.post("/predict", json={**VALID, "farm_id": "B", "payment_delay_days": 0,
                                  "previous_defaults": 0, "debt": 0, "precipitation_mm": 500})  # low
    assert [i["farm_id"] for i in client.get("/predictions").json()] == ["B", "A"]
    assert len(client.get("/predictions?limit=1").json()) == 1
    assert all(i["risk_level"] == "high" for i in client.get("/predictions?risk_level=high").json())


@pytest.mark.parametrize("q", ["limit=-5", "limit=0", "limit=101"])
def test_list_limit_422(q):
    assert client.get(f"/predictions?{q}").status_code == 422


def test_list_bad_risk_level_400():
    assert client.get("/predictions?risk_level=extreme").status_code == 400
