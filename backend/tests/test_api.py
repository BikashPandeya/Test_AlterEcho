from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data_mode"] == "mixed"
    assert response.json()["data_counts"]["real_processed_sites"] >= 1


def test_catalog_and_earth_filter():
    sites = client.get("/api/sites?body=earth").json()
    assert sites
    assert all(site["body"] == "earth" for site in sites)
    assert client.get("/api/sites/mars-jezero").json()["name"] == "Jezero Crater"


def test_discover_schema_and_unknown_site():
    response = client.post("/api/discover", json={"reference_site_id": "mars-jezero", "candidate_site_ids": ["earth-atacama"]})
    assert response.status_code == 200
    assert response.json()["results"][0]["data_status"] == "real_processed"
    missing = client.post("/api/discover", json={"reference_site_id": "mars-jezero", "candidate_site_ids": ["missing"]})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "candidate_not_found"


def test_negative_and_zero_weights_rejected():
    payload = {"reference_site_id": "mars-jezero", "candidate_site_ids": ["earth-atacama"]}
    assert client.post("/api/discover", json={**payload, "weights": {"slope_p50_deg": -1}}).status_code == 422
    assert client.post("/api/discover", json={**payload, "weights": {"slope_p50_deg": 0}}).status_code == 422

