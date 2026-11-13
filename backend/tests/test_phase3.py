import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.scripts.acquire_dataset import AcquisitionError, earthdata_headers
from app.services.geospatial_service import load_aoi, validate_processing_report
from app.services.srtm_service import redact_secret, srtm_archive_name, tiles_for_bounds, tiles_for_geojson_geometry


client = TestClient(app)


def test_srtm_tile_calculation_for_all_phase3_aois():
    assert tiles_for_geojson_geometry(load_aoi("earth-atacama-aoi-v1").geometry) == ["S25W070"]
    assert tiles_for_geojson_geometry(load_aoi("earth-upper-mustang-aoi-v1").geometry) == ["N29E083"]
    assert tiles_for_geojson_geometry(load_aoi("earth-ladakh-aoi-v1").geometry) == ["N34E077"]
    assert srtm_archive_name("N29E083") == "N29E083.SRTMGL1.hgt.zip"


def test_aoi_crossing_boundaries_requires_multiple_tiles():
    assert tiles_for_bounds(83.95, 29.95, 84.05, 30.05) == ["N29E083", "N29E084", "N30E083", "N30E084"]


def test_earthdata_auth_failure_and_secret_redaction():
    with pytest.raises(AcquisitionError, match="credentials missing"):
        earthdata_headers({})
    token = "sensitive-token-value"
    assert token not in redact_secret(f"request failed using Bearer {token}", f"Bearer {token}")


def test_health_reports_mixed_counts():
    payload = client.get("/api/health").json()
    assert payload["data_mode"] == "mixed"
    assert payload["data_counts"]["real_processed_sites"] >= 1
    assert payload["data_counts"]["demo_fixture_sites"] >= 1
    assert payload["data_counts"]["rankable_real_candidates"] == 3


def test_preview_ranking_is_separate_and_metadata_has_no_score():
    payload = client.post("/api/discover", json={"reference_site_id":"mars-jezero","candidate_site_ids":["earth-holuhraun", "earth-danakil"]}).json()
    assert payload["ranking_scope"] == "preview_only" and payload["real_results"] == []
    assert len(payload["preview_results"]) == 2
    danakil = next(item for item in payload["preview_results"] if item["candidate_site"]["id"] == "earth-danakil")
    assert danakil["overall_similarity"] is None
    assert danakil["comparison_classification"] == "not_rankable_metadata"


def test_stale_processing_output_checksum_is_rejected(tmp_path, monkeypatch):
    import app.services.geospatial_service as geo
    backend = tmp_path / "backend"; summary = backend / "data" / "processed" / "summary.json"
    summary.parent.mkdir(parents=True); summary.write_text("original", encoding="utf-8")
    report = tmp_path / "run.json"; report.write_text(json.dumps({"output_summary":"data/processed/summary.json", "output_checksum":"wrong"}), encoding="utf-8")
    monkeypatch.setattr(geo, "BACKEND_ROOT", backend)
    with pytest.raises(ValueError, match="checksum is stale"):
        validate_processing_report(report)
