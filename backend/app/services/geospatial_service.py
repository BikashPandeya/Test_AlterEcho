from datetime import datetime, timezone
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
from uuid import uuid4
import numpy as np

from app.models.schemas import AOIRecord, DataStatus, SourceManifest, TerrainFeatureSummary
from app.services.terrain_service import summarize_array, write_summary

BACKEND_ROOT = Path(__file__).resolve().parents[2]
GEO_DATA = BACKEND_ROOT / "data"


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def load_manifest(source_id: str) -> SourceManifest:
    return SourceManifest.model_validate_json((GEO_DATA / "manifests" / f"{source_id}.json").read_text(encoding="utf-8"))


def write_manifest(manifest: SourceManifest) -> None:
    (GEO_DATA / "manifests" / f"{manifest.source_id}.json").write_text(json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8")


def load_aoi(aoi_id: str) -> AOIRecord:
    payload = json.loads((GEO_DATA / "aoi" / f"{aoi_id}.geojson").read_text(encoding="utf-8"))
    return AOIRecord(**payload["properties"], geometry=payload["geometry"])


def list_aois() -> list[AOIRecord]:
    return [load_aoi(path.stem) for path in sorted((GEO_DATA / "aoi").glob("*.geojson"))]


def metric_grid_size(width_m: float, height_m: float, resolution_m: float) -> tuple[int, int, float, float]:
    if resolution_m <= 0 or width_m <= 0 or height_m <= 0: raise ValueError("AOI dimensions and target resolution must be positive")
    columns, rows = ceil(width_m / resolution_m), ceil(height_m / resolution_m)
    return columns, rows, columns * resolution_m, rows * resolution_m


def validate_processing_report(report_path: str | Path) -> dict:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    summary_path = BACKEND_ROOT / report["output_summary"]
    if not summary_path.exists():
        raise ValueError("Processed output referenced by the run is missing")
    actual = sha256_file(summary_path)
    if actual != report.get("output_checksum"):
        raise ValueError("Processed output checksum is stale or does not match the processing run")
    return report


def _analysis_crs(dataset_crs, body: str, longitude: float, latitude: float):
    from rasterio.crs import CRS
    if body == "mars":
        if not dataset_crs or not dataset_crs.is_projected: raise ValueError("Mars DEM must provide a projected planetary CRS")
        if dataset_crs.linear_units.lower() not in {"metre", "meter", "metres", "meters"}: raise ValueError(f"Mars projected CRS must use metres, found {dataset_crs.linear_units}")
        return dataset_crs
    zone = floor((longitude + 180) / 6) + 1
    return CRS.from_epsg((32600 if latitude >= 0 else 32700) + zone)


def _center_in_crs(analysis_crs, body: str, longitude: float, latitude: float) -> tuple[float, float]:
    from rasterio.crs import CRS
    from rasterio.warp import transform
    geographic = CRS.from_string("+proj=longlat +a=3396190 +b=3396190 +no_defs") if body == "mars" else CRS.from_epsg(4326)
    xs, ys = transform(geographic, analysis_crs, [longitude], [latitude])
    return xs[0], ys[0]


def process_site(input_path: str | Path, site_id: str, aoi_id: str, source_id: str, target_resolution_m: float = 60.0) -> tuple[TerrainFeatureSummary, dict]:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
    source_path = Path(input_path); manifest, aoi = load_manifest(source_id), load_aoi(aoi_id)
    source_checksum = sha256_file(source_path); expected = manifest.mosaic_sha256_checksum or manifest.extracted_sha256_checksum or manifest.sha256_checksum
    if expected and source_checksum != expected: raise ValueError("Input checksum differs from the source manifest")
    if aoi.site_id != site_id: raise ValueError("AOI site_id does not match requested site")
    columns, rows, actual_width, actual_height = metric_grid_size(aoi.width_m, aoi.height_m, target_resolution_m)
    processed_at = datetime.now(timezone.utc)
    run_id = f"{site_id}-{processed_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"; warnings_list: list[str] = []
    with rasterio.open(source_path) as dataset:
        if dataset.crs is None: raise ValueError("Source raster has no CRS")
        analysis_crs = _analysis_crs(dataset.crs, aoi.planetary_body, aoi.center_longitude, aoi.center_latitude)
        center_x, center_y = _center_in_crs(analysis_crs, aoi.planetary_body, aoi.center_longitude, aoi.center_latitude)
        target_transform = from_origin(center_x - actual_width / 2, center_y + actual_height / 2, target_resolution_m, target_resolution_m)
        destination = np.full((rows, columns), np.nan, dtype="float32")
        reproject(source=rasterio.band(dataset, 1), destination=destination, src_transform=dataset.transform, src_crs=dataset.crs, src_nodata=dataset.nodata, dst_transform=target_transform, dst_crs=analysis_crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
        native_resolution, source_crs = list(dataset.res), str(dataset.crs)
    valid_mask = np.isfinite(destination); coverage = float(valid_mask.mean())
    if not valid_mask.any(): raise ValueError("AOI has no intersection with valid source elevation cells")
    if coverage < 0.90: warnings_list.append(f"Valid coverage {coverage:.3f} is below the 0.90 real-data gate")
    provenance = {"source_id": source_id, "source_checksum": source_checksum, "source_manifest": f"data/manifests/{source_id}.json", "aoi_id": aoi_id, "aoi_version": aoi.version, "processing_run_id": run_id, "methodology_version": "terrain-v2.0", "processed_at": processed_at.isoformat()}
    real_ready = bool(source_checksum and coverage >= 0.90 and expected and aoi_id and manifest.source_page_url)
    summary = summarize_array(site_id, destination, target_resolution_m, target_resolution_m, str(analysis_crs), source_id, valid_mask=valid_mask, data_status=DataStatus.real_processed if real_ready else DataStatus.unavailable, provenance=provenance, aoi_id=aoi_id, processing_run_id=run_id, analysis_width_m=actual_width, analysis_height_m=actual_height)
    summary.quality["warnings"] = warnings_list + summary.quality.get("warnings", [])
    interim = GEO_DATA / "interim" / f"{site_id}-{run_id}.harmonized.tif"; interim.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(interim, "w", driver="GTiff", height=rows, width=columns, count=1, dtype="float32", crs=analysis_crs, transform=target_transform, nodata=np.nan, compress="deflate") as output: output.write(destination, 1)
    summary_path = GEO_DATA / "processed" / f"{site_id}.terrain.json"; write_summary(summary, summary_path); output_checksum = sha256_file(summary_path)
    report = {"processing_run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "site_id": site_id, "source_id": source_id, "source_checksum": source_checksum, "aoi_version": aoi.version, "methodology_version": "terrain-v2.0", "software_version": "0.2.0", "native_resolution": native_resolution, "target_resolution": target_resolution_m, "source_crs": source_crs, "processing_crs": str(analysis_crs), "resampling_method": "bilinear", "nodata_handling": "Source nodata is propagated to NaN and excluded from every metric", "requested_analysis_window_m": [aoi.width_m, aoi.height_m], "actual_analysis_window_m": [actual_width, actual_height], "grid_dimensions": [columns, rows], "metric_configuration": summary.calculation_metadata, "output_summary": str(summary_path.relative_to(BACKEND_ROOT)), "output_checksum": output_checksum, "quality_passed": real_ready, "warnings": summary.quality["warnings"]}
    report_path = GEO_DATA / "processed" / f"{run_id}.processing.json"; report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest.processing_status = "processed" if real_ready else "quality_failed"
    manifest.notes = "Downloaded file was checksummed, inspected, and processed through the terrain-v2.0 pipeline." if real_ready else "Processing completed but one or more real-data quality gates failed."
    write_manifest(manifest)
    return summary, report
