from math import floor
from pathlib import Path
import re


def srtm_tile_id(latitude: int, longitude: int) -> str:
    lat_prefix = "N" if latitude >= 0 else "S"
    lon_prefix = "E" if longitude >= 0 else "W"
    return f"{lat_prefix}{abs(latitude):02d}{lon_prefix}{abs(longitude):03d}"


def tiles_for_bounds(west: float, south: float, east: float, north: float) -> list[str]:
    if west >= east or south >= north:
        raise ValueError("Invalid AOI bounds")
    epsilon = 1e-10
    latitudes = range(floor(south), floor(north - epsilon) + 1)
    longitudes = range(floor(west), floor(east - epsilon) + 1)
    return [srtm_tile_id(latitude, longitude) for latitude in latitudes for longitude in longitudes]


def tiles_for_geojson_geometry(geometry: dict) -> list[str]:
    if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
        raise ValueError("AOI must contain a Polygon geometry")
    ring = geometry["coordinates"][0]
    longitudes = [point[0] for point in ring]
    latitudes = [point[1] for point in ring]
    return tiles_for_bounds(min(longitudes), min(latitudes), max(longitudes), max(latitudes))


def srtm_archive_name(tile_id: str) -> str:
    if not re.fullmatch(r"[NS]\d{2}[EW]\d{3}", tile_id):
        raise ValueError(f"Invalid SRTM tile ID: {tile_id}")
    return f"{tile_id}.SRTMGL1.hgt.zip"


def srtm_download_url(tile_id: str) -> str:
    granule_name = f"{tile_id}.SRTMGL1.hgt"
    return f"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL1.003/{granule_name}/{granule_name}.zip"


def redact_secret(message: str, secret: str | None) -> str:
    return message.replace(secret, "[REDACTED]") if secret else message


def mosaic_rasters(inputs: list[str | Path], output: str | Path) -> Path:
    if not inputs:
        raise ValueError("At least one SRTM tile is required")
    import rasterio
    from rasterio.merge import merge
    datasets = [rasterio.open(path) for path in inputs]
    try:
        crs_values = {str(dataset.crs) for dataset in datasets}
        if len(crs_values) != 1:
            raise ValueError("SRTM tiles must share one CRS before mosaicking")
        mosaic, transform = merge(datasets, nodata=datasets[0].nodata)
        profile = datasets[0].profile.copy()
        profile.update(width=mosaic.shape[2], height=mosaic.shape[1], transform=transform, count=1, compress="deflate")
        destination = Path(output); destination.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(destination, "w", **profile) as target:
            target.write(mosaic[0], 1)
        return destination
    finally:
        for dataset in datasets: dataset.close()

