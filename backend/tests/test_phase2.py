import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import DataStatus, TerrainFeatureSummary
from app.services.geospatial_service import load_aoi, metric_grid_size, sha256_file
from app.services.similarity_service import check_compatibility
import app.services.geospatial_service as geo


client = TestClient(app)


def test_sha256_and_equal_aoi_dimensions(tmp_path):
    sample = tmp_path / "sample.bin"; sample.write_bytes(b"terraluna")
    assert sha256_file(sample) == "76d9f4a4c5bd4ca91bc93f827c6492645f4409f2f2c1ac543b9e6920cace1213"
    jezero, atacama = load_aoi("mars-jezero-aoi-v1"), load_aoi("earth-atacama-aoi-v1")
    assert (jezero.width_m, jezero.height_m) == (atacama.width_m, atacama.height_m) == (10000, 10000)
    assert metric_grid_size(10000, 10000, 60) == (167, 167, 10020, 10020)


def test_real_status_rejected_without_provenance():
    with pytest.raises(ValueError, match="real_processed requires provenance"):
        TerrainFeatureSummary(site_id="bad", valid_coverage_fraction=1, calculation_metadata={}, data_source="x", data_status=DataStatus.real_processed)


def test_incompatible_resolution_and_methodology_are_reported():
    first = TerrainFeatureSummary(site_id="a", valid_coverage_fraction=1, resolution_m=60, analysis_width_m=10020, analysis_height_m=10020, calculation_metadata={"methodology_version":"terrain-v2.0"}, data_source="fixture", data_status=DataStatus.demo_fixture)
    second = TerrainFeatureSummary(site_id="b", valid_coverage_fraction=1, resolution_m=90, analysis_width_m=9000, analysis_height_m=9000, calculation_metadata={"methodology_version":"other"}, data_source="fixture", data_status=DataStatus.demo_fixture)
    compatibility = check_compatibility(first, second)
    assert not compatibility.compatible
    assert not compatibility.resolution_match and not compatibility.aoi_scale_match and not compatibility.methodology_match
    assert len(compatibility.warnings) == 4


def test_phase2_endpoints_and_discover_compatibility():
    aoi = client.get("/api/sites/earth-atacama/aoi")
    assert aoi.status_code == 200 and aoi.json()["properties"]["width_m"] == 10000
    terrain = client.get("/api/sites/mars-jezero/terrain")
    assert terrain.status_code == 200 and terrain.json()["data_status"] == "real_processed"
    run_id = terrain.json()["processing_run_id"]
    assert client.get(f"/api/processing-runs/{run_id}").status_code == 200
    sources = client.get("/api/sources")
    assert sources.status_code == 200 and len(sources.json()) >= 4
    result = client.post("/api/discover", json={"reference_site_id": "mars-jezero", "candidate_site_ids": ["earth-atacama"]}).json()["results"][0]
    assert result["data_status"] == "real_processed"
    assert result["comparison_classification"] == "real_comparison"
    assert result["compatibility"]["compatible"]
    assert result["provenance"]["notice"].startswith("Comparison generated")


def test_generated_raster_is_transformed_harmonized_and_preserves_nodata(tmp_path, monkeypatch):
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.warp import transform

    backend_root = tmp_path / "backend"; data_root = backend_root / "data"
    for folder in ("manifests", "aoi", "processed", "interim"): (data_root / folder).mkdir(parents=True)
    monkeypatch.setattr(geo, "BACKEND_ROOT", backend_root); monkeypatch.setattr(geo, "GEO_DATA", data_root)
    crs = CRS.from_epsg(32719)
    center_x, center_y = (values[0] for values in transform(CRS.from_epsg(4326), crs, [-69.9], [-24.2]))
    raster = np.tile(np.arange(400, dtype="float32") * 3, (400, 1)); raster[190:210, 190:210] = -9999
    source = tmp_path / "source.tif"
    with rasterio.open(source, "w", driver="GTiff", width=400, height=400, count=1, dtype="float32", crs=crs, transform=from_origin(center_x - 6000, center_y + 6000, 30, 30), nodata=-9999) as dst: dst.write(raster, 1)
    checksum = sha256_file(source)
    manifest = {"source_id":"test-source","title":"Generated test DEM","planetary_body":"earth","provider":"test","mission":None,"instrument":None,"product_name":"fixture","product_version":"1","source_page_url":"https://example.test","download_url":None,"doi":None,"access_date":"2026-11-13","license_or_use_constraints":"test only","native_resolution":[30,30],"native_crs":str(crs),"native_bounds":None,"native_nodata":-9999,"file_size":source.stat().st_size,"filename":source.name,"sha256_checksum":checksum,"citation_text":"generated test","processing_status":"inspected","notes":"unit-test fixture"}
    (data_root / "manifests" / "test-source.json").write_text(json.dumps(manifest), encoding="utf-8")
    aoi = {"type":"Feature","properties":{"aoi_id":"test-aoi","site_id":"test-site","version":"1","planetary_body":"earth","center_latitude":-24.2,"center_longitude":-69.9,"width_m":10000,"height_m":10000,"selection_rationale":"test","intended_analog_characteristics":[],"known_limitations":[],"creation_method":"generated","source_references":["test-source"]},"geometry":{"type":"Polygon","coordinates":[]}}
    (data_root / "aoi" / "test-aoi.geojson").write_text(json.dumps(aoi), encoding="utf-8")
    summary, report = geo.process_site(source, "test-site", "test-aoi", "test-source", 60)
    assert summary.data_status == DataStatus.real_processed
    assert summary.resolution_m == 60 and summary.analysis_width_m == 10020
    assert 0.90 < summary.valid_coverage_fraction < 1
    assert summary.slope_p50_deg == pytest.approx(np.degrees(np.arctan(0.1)), abs=0.2)
    assert report["resampling_method"] == "bilinear"
