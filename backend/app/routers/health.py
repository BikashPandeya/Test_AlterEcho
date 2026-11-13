from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.services.catalog_service import data_status_summary


router = APIRouter()


@router.get("/health")
def health():
    summary = data_status_summary()
    return {"status": "online", "application_version": settings.app_version, "methodology_version": settings.methodology_version, "data_mode": summary.pop("data_mode"), "data_counts": summary, "timestamp": datetime.now(timezone.utc)}


@router.get("/config")
def config():
    summary = data_status_summary()
    return {"enabled_bodies": ["earth", "mars", "moon"], "enabled_features": ["catalog", "terrain_comparison", "dem_processing_foundation", "real_preview_separation", "srtm_multi_tile_mosaic"], "backend_mode": summary["data_mode"], "data_counts": {key: value for key, value in summary.items() if key != "data_mode"}, "methodology_version": settings.methodology_version}

