from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Body, DataStatus
from app.services import catalog_service


router = APIRouter()


@router.get("/planets")
def planets():
    return catalog_service.PLANETS


@router.get("/sites")
def sites(body: Body | None = None, data_status: DataStatus | None = None, analog_type: str | None = Query(default=None, max_length=80)):
    return catalog_service.list_sites(body.value if body else None, data_status.value if data_status else None, analog_type)


@router.get("/sites/{site_id}")
def site(site_id: str):
    result = catalog_service.get_site(site_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "site_not_found", "message": f"Unknown site ID: {site_id}"})
    return result


@router.get("/methodology")
def methodology():
    return {
        "version": "terrain-v2.0",
        "metrics": ["median and 90th-percentile slope", "median and 90th-percentile local relief over 1,000 m", "mean and 90th-percentile local elevation standard deviation over 300 m"],
        "formula": "Per metric: exp(-0.5 * (difference / tolerance)^2); valid metrics are combined with normalized weights.",
        "data_statuses": {"real_processed": "Computed from a traceable source raster", "demo_fixture": "Synthetic values used only to exercise the application", "metadata_only": "Catalog context without computed metrics", "unavailable": "Not available"},
        "harmonization": "Equal-scale 10 km requested AOIs are bilinearly resampled to a common 60 m grid before terrain derivatives. The 167-cell grid has an actual 10,020 m extent.",
        "ranking_gate": "Real comparisons require matching AOI scale, resolution, methodology, provenance, and at least 90% valid coverage.",
        "limitations": ["Phase 2 compares terrain shape only and excludes absolute elevation datum from similarity", "Scores are comparison indices, not probabilities", "Earth cannot reproduce planetary gravity, pressure, radiation, geology, temperature cycles, or habitability"],
    }

