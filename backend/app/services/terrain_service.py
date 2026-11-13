from pathlib import Path
import json
import warnings
import numpy as np

from app.models.schemas import DataStatus, TerrainFeatureSummary


def _mask(elevation: np.ndarray, valid_mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(elevation, dtype=float)
    mask = np.isfinite(values) if valid_mask is None else (np.asarray(valid_mask, dtype=bool) & np.isfinite(values))
    return values, mask


def physical_window_pixels(neighborhood_m: float, resolution_m: float) -> int:
    if neighborhood_m <= 0 or resolution_m <= 0:
        raise ValueError("Neighborhood and resolution must be positive")
    pixels = max(3, int(round(neighborhood_m / resolution_m)))
    return pixels if pixels % 2 else pixels + 1


def calculate_slope(elevation: np.ndarray, resolution_x_m: float, resolution_y_m: float, valid_mask: np.ndarray | None = None) -> np.ndarray:
    values, mask = _mask(elevation, valid_mask)
    dz_dy, dz_dx = np.gradient(np.where(mask, values, np.nan), resolution_y_m, resolution_x_m)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    slope[~mask] = np.nan
    return slope


def _windows(elevation: np.ndarray, window_size: int, valid_mask: np.ndarray | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if window_size < 3 or window_size % 2 == 0:
        raise ValueError("window_size must be an odd integer of at least 3")
    values, mask = _mask(elevation, valid_mask)
    padded = np.pad(np.where(mask, values, np.nan), window_size // 2, constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, (window_size, window_size))
    sufficient = np.count_nonzero(np.isfinite(windows), axis=(-2, -1)) >= window_size * window_size * 0.5
    return windows, mask, sufficient


def calculate_local_relief(elevation: np.ndarray, window_size: int = 3, valid_mask: np.ndarray | None = None) -> np.ndarray:
    windows, mask, sufficient = _windows(elevation, window_size, valid_mask)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = np.nanmax(windows, axis=(-2, -1)) - np.nanmin(windows, axis=(-2, -1))
    result[~mask | ~sufficient] = np.nan
    return result


def calculate_roughness(elevation: np.ndarray, window_size: int = 3, valid_mask: np.ndarray | None = None) -> np.ndarray:
    """Local elevation standard deviation in metres over the declared physical neighborhood."""
    windows, mask, sufficient = _windows(elevation, window_size, valid_mask)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = np.nanstd(windows, axis=(-2, -1))
    result[~mask | ~sufficient] = np.nan
    return result


def _stat(values: np.ndarray, operation, *args) -> float | None:
    valid = values[np.isfinite(values)]
    return float(operation(valid, *args)) if valid.size else None


def summarize_array(site_id: str, elevation: np.ndarray, resolution_x_m: float, resolution_y_m: float, projection: str, data_source: str, valid_mask: np.ndarray | None = None, local_relief_neighborhood_m: float = 1000.0, roughness_neighborhood_m: float = 300.0, data_status: DataStatus = DataStatus.demo_fixture, provenance: dict | None = None, aoi_id: str | None = None, processing_run_id: str | None = None, analysis_width_m: float | None = None, analysis_height_m: float | None = None, window_size: int | None = None) -> TerrainFeatureSummary:
    values, mask = _mask(elevation, valid_mask)
    resolution = float(max(abs(resolution_x_m), abs(resolution_y_m)))
    relief_pixels = window_size or physical_window_pixels(local_relief_neighborhood_m, resolution)
    roughness_pixels = physical_window_pixels(roughness_neighborhood_m, resolution)
    slope = calculate_slope(values, resolution_x_m, resolution_y_m, mask)
    relief = calculate_local_relief(values, relief_pixels, mask)
    roughness = calculate_roughness(values, roughness_pixels, mask)
    valid_elevation = np.where(mask, values, np.nan)
    slope_max = _stat(slope, np.max)
    quality_warnings = [f"Extreme slope artifact check: maximum slope is {slope_max:.2f} degrees"] if slope_max is not None and slope_max > 60 else []
    return TerrainFeatureSummary(
        site_id=site_id, elevation_min_m=_stat(valid_elevation, np.min), elevation_max_m=_stat(valid_elevation, np.max), elevation_mean_m=_stat(valid_elevation, np.mean), elevation_std_m=_stat(valid_elevation, np.std), elevation_p10_m=_stat(valid_elevation, np.percentile, 10), elevation_p50_m=_stat(valid_elevation, np.percentile, 50), elevation_p90_m=_stat(valid_elevation, np.percentile, 90),
        slope_mean_deg=_stat(slope, np.mean), slope_p50_deg=_stat(slope, np.percentile, 50), slope_p90_deg=_stat(slope, np.percentile, 90), slope_max_deg=slope_max,
        local_relief_m=_stat(relief, np.percentile, 50), local_relief_mean_m=_stat(relief, np.mean), local_relief_p50_m=_stat(relief, np.percentile, 50), local_relief_p90_m=_stat(relief, np.percentile, 90), roughness_index=_stat(roughness, np.mean), roughness_mean=_stat(roughness, np.mean), roughness_p90=_stat(roughness, np.percentile, 90),
        valid_coverage_fraction=float(mask.mean()), resolution_m=resolution, projection=projection,
        calculation_metadata={"methodology_version": "terrain-v2.0", "slope_method": "central differences using metric x/y spacing", "local_relief_definition": "local maximum minus local minimum", "local_relief_neighborhood_m": local_relief_neighborhood_m, "local_relief_window_pixels": relief_pixels, "roughness_definition": "local elevation standard deviation", "roughness_neighborhood_m": roughness_neighborhood_m, "roughness_window_pixels": roughness_pixels},
        data_source=data_source, data_status=data_status, aoi_id=aoi_id, processing_run_id=processing_run_id, analysis_width_m=analysis_width_m, analysis_height_m=analysis_height_m, provenance=provenance or {}, quality={"warnings": quality_warnings, "non_finite_cell_count": int(values.size - mask.sum())})


def inspect_dem(path: str | Path) -> dict:
    import rasterio
    with rasterio.open(path) as dataset:
        mask = dataset.dataset_mask() > 0
        return {"path": str(path), "driver": dataset.driver, "dtype": dataset.dtypes[0], "count": dataset.count, "crs": str(dataset.crs) if dataset.crs else None, "is_projected": bool(dataset.crs and dataset.crs.is_projected), "linear_units": dataset.crs.linear_units if dataset.crs and dataset.crs.is_projected else None, "resolution": list(dataset.res), "nodata": dataset.nodata, "bounds": list(dataset.bounds), "width": dataset.width, "height": dataset.height, "valid_coverage_fraction": float(mask.mean())}


def process_dem(path: str | Path, site_id: str) -> TerrainFeatureSummary:
    import rasterio
    with rasterio.open(path) as dataset:
        if not dataset.crs or not dataset.crs.is_projected:
            raise ValueError("Terrain calculations require a projected CRS with verified metric units")
        elevation = dataset.read(1, masked=True)
        return summarize_array(site_id, elevation.filled(np.nan), abs(dataset.res[0]), abs(dataset.res[1]), str(dataset.crs), str(path), ~elevation.mask)


def write_summary(summary: TerrainFeatureSummary, output: str | Path) -> None:
    destination = Path(output); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary.model_dump(mode="json"), indent=2), encoding="utf-8")

