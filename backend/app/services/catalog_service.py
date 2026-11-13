import json
from pathlib import Path

from app.models.schemas import Planet, Site, SourceReference, TerrainFeatureSummary
from app.services.geospatial_service import GEO_DATA


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read_json(filename: str):
    with (DATA_DIR / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


PLANETS = [Planet.model_validate(item) for item in _read_json("planets.json")]
SITES = [Site.model_validate(item) for item in _read_json("sites.json")]
SOURCES = [SourceReference.model_validate(item) for item in _read_json("sources.json")]
_DEMO = _read_json("comparisons.demo.json")
FEATURES = {
    site_id: TerrainFeatureSummary(site_id=site_id, **values)
    for site_id, values in _DEMO["features"].items()
}


def list_sites(body: str | None = None, data_status: str | None = None, analog_type: str | None = None) -> list[Site]:
    sites = [_with_processed_status(site) for site in SITES]
    return [
        site for site in sites
        if (body is None or site.body.value == body)
        and (data_status is None or site.data_status.value == data_status)
        and (analog_type is None or site.analog_type == analog_type)
    ]


def get_site(site_id: str) -> Site | None:
    site = next((site for site in SITES if site.id == site_id), None)
    return _with_processed_status(site) if site else None


def get_feature_summary(site_id: str) -> TerrainFeatureSummary | None:
    return FEATURES.get(site_id)


def get_processed_summary(site_id: str) -> TerrainFeatureSummary | None:
    path = GEO_DATA / "processed" / f"{site_id}.terrain.json"
    return TerrainFeatureSummary.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def _with_processed_status(site: Site) -> Site:
    processed = get_processed_summary(site.id)
    if not processed or processed.data_status.value != "real_processed":
        return site
    available = [name for name in ("slope_p50_deg", "slope_p90_deg", "local_relief_p50_m", "local_relief_p90_m", "roughness_mean", "roughness_p90") if getattr(processed, name) is not None]
    return site.model_copy(update={"data_status": processed.data_status, "available_metrics": available})


def data_status_summary() -> dict[str, int | str]:
    sites = [_with_processed_status(site) for site in SITES]
    counts = {f"{status}_sites": sum(site.data_status.value == status for site in sites) for status in ("real_processed", "demo_fixture", "metadata_only", "unavailable")}
    if counts["real_processed_sites"] and (counts["demo_fixture_sites"] or counts["metadata_only_sites"] or counts["unavailable_sites"]):
        mode = "mixed"
    elif counts["real_processed_sites"]:
        mode = "real"
    elif counts["demo_fixture_sites"]:
        mode = "demo"
    else:
        mode = "unavailable"
    counts["data_mode"] = mode
    counts["rankable_real_candidates"] = sum(site.body.value == "earth" and site.data_status.value == "real_processed" and len(site.available_metrics) >= 4 for site in sites)
    return counts

