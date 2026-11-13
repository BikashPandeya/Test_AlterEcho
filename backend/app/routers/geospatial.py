import json

from fastapi import APIRouter, HTTPException

from app.models.schemas import ProcessingRun, SourceManifest, TerrainFeatureSummary
from app.services.catalog_service import get_feature_summary, get_processed_summary, get_site
from app.services.geospatial_service import GEO_DATA, load_aoi, load_manifest

router = APIRouter()


@router.get("/sites/{site_id}/aoi")
def site_aoi(site_id: str):
    site = get_site(site_id)
    if not site: raise HTTPException(status_code=404, detail={"code": "site_not_found", "message": f"Unknown site ID: {site_id}"})
    matches = list((GEO_DATA / "aoi").glob(f"{site_id}-aoi-*.geojson"))
    if not matches: raise HTTPException(status_code=404, detail={"code": "aoi_not_found", "message": f"No AOI is registered for {site_id}"})
    return json.loads(matches[-1].read_text(encoding="utf-8"))


@router.get("/sites/{site_id}/terrain", response_model=TerrainFeatureSummary)
def site_terrain(site_id: str):
    if not get_site(site_id): raise HTTPException(status_code=404, detail={"code": "site_not_found", "message": f"Unknown site ID: {site_id}"})
    summary = get_processed_summary(site_id) or get_feature_summary(site_id)
    if not summary: raise HTTPException(status_code=404, detail={"code": "terrain_unavailable", "message": f"No terrain summary is available for {site_id}"})
    return summary


@router.get("/sources", response_model=list[SourceManifest])
def sources():
    return [load_manifest(path.stem) for path in sorted((GEO_DATA / "manifests").glob("*.json"))]


@router.get("/sources/{source_id}", response_model=SourceManifest)
def source(source_id: str):
    path = GEO_DATA / "manifests" / f"{source_id}.json"
    if not path.exists(): raise HTTPException(status_code=404, detail={"code": "source_not_found", "message": f"Unknown source ID: {source_id}"})
    return load_manifest(source_id)


@router.get("/processing-runs/{run_id}", response_model=ProcessingRun)
def processing_run(run_id: str):
    path = GEO_DATA / "processed" / f"{run_id}.processing.json"
    if not path.exists(): raise HTTPException(status_code=404, detail={"code": "processing_run_not_found", "message": f"Unknown processing run: {run_id}"})
    return ProcessingRun.model_validate_json(path.read_text(encoding="utf-8"))
