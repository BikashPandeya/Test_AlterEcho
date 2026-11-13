# TerraLuna AI - Phase 3

TerraLuna AI is Team AlterEcho's transparent terrain-analog explorer. Phase 3 preserves the Next.js/MapLibre/Three.js and FastAPI architecture, adds SRTM tile/mosaic acquisition for three Earth candidates, synchronized candidate focus and selection, real/demo ranking separation, mixed-data health counts, compact responsive panels, and Playwright browser coverage.

## Current scientific status

- **Jezero Crater:** `real_processed`. The official 20 m USGS/PDS CTX DEM was downloaded, SHA-256 verified, inspected, cropped around the versioned AOI, resampled to 60 m, processed, and passed the 0.90 coverage gate with 1.0 valid coverage.
- **Atacama, Upper Mustang, and Ladakh:** `real_processed`. Each has an authenticated SRTMGL1.003 source, recorded checksum, inspected native metadata, a 10 km × 10 km AOI, and a validated 60 m terrain-v2.0 summary.
- The discovery endpoint ranks these three Earth candidates only against the real Jezero summary. Demo and metadata-only candidates remain in separate preview/non-rankable scopes and are never mixed with real metrics.
- **Holuhraun, McMurdo, and Danakil:** remain demo or metadata-only. Holuhraun and McMurdo require polar DEM products rather than SRTM; Danakil still lacks a versioned terrain AOI.
- Display coordinates and AOI outlines are research locators, not claims that an entire region is a measured analog.

## Repository and data layout

```text
frontend/                     Next.js interface
backend/app/                  FastAPI, schemas, services, and CLIs
backend/app/data/             API catalog and versioned similarity configuration
backend/data/manifests/       Machine-readable source provenance
backend/data/aoi/             Versioned GeoJSON study windows
backend/data/processed/       Small terrain summaries and processing reports
backend/data/sources/         Optional small provider records
backend/data/raw/             Ignored source rasters
backend/data/interim/         Ignored harmonized rasters
backend/data/cache/           Ignored temporary downloads
```

Raw and interim rasters are deliberately excluded from Git because the Jezero source alone is 90,345,300 bytes. The application reads committed processed JSON and does not require a raw DEM at runtime.

## Dataset sources and citations

### Jezero

- Product: Mars 2020 Science Investigation CTX DEM Mosaic, 20 m/pixel
- Provider: USGS Astrogeology Science Center / Planetary Data System
- Source record: <https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic>
- DOI: <https://doi.org/10.5066/P906QQT8>
- Exact filename: `M20_JezeroCrater_CTXDEM_20m.tif`
- Recorded SHA-256: `ba7f706ea1b5d63a562f28a7dcf7a7f3c79bce7f048e6974b57e8a33c30d1ba2`

### Atacama

- Product: NASA SRTM Global 1 Arc Second V003 (`SRTMGL1.003`)
- Provider: NASA LP DAAC / USGS EROS
- DOI: <https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003>
- Earthdata search: <https://search.earthdata.nasa.gov/search?q=SRTMGL1>
- Tile containing the AOI center: `S25W070.SRTMGL1.hgt.zip`; extracted input: `S25W070.hgt`

### Phase 3 SRTM candidates

- Upper Mustang AOI: `earth-upper-mustang-aoi-v1`, tile `N29E083`, center 29.10 N, 83.90 E.
- Ladakh AOI: `earth-ladakh-aoi-v1`, tile `N34E077`, center 34.20 N, 77.60 E.
- The acquisition utility derives all intersecting tiles from each AOI; it does not assume a single tile. Multi-tile inputs are checksummed and mosaicked before processing.

Use the complete citation strings and access metadata in `backend/data/manifests/` when presenting results.

## AOIs and harmonization

Both AOIs request 10,000 m × 10,000 m windows:

- `mars-jezero-aoi-v1`: centered at 18.44° N, 77.45° E.
- `earth-atacama-aoi-v1`: centered at 24.20° S, 69.90° W.

Processing builds an exact metric grid around each center. The common resolution is 60 m/pixel. Because 10,000 is not divisible by 60, the deterministic grid is 167 × 167 cells and the recorded actual extent is 10,020 m × 10,020 m. Elevation is bilinearly resampled before derivatives. Mars retains the source equirectangular metric CRS; Atacama is analyzed in local UTM zone 19S.

## Terrain-v2.0 method

Metrics use only valid masked cells:

- elevation minimum, maximum, mean, standard deviation, and p10/p50/p90 for description only;
- slope from central differences using physical x/y spacing;
- local relief as local maximum minus local minimum over a 1,000 m neighborhood;
- roughness as local elevation standard deviation over a 300 m neighborhood;
- mean, median, p90, maximum, coverage, and quality warnings as applicable.

Absolute Earth/Mars elevation is not scored because the bodies use different vertical datums. Default comparison features are slope p50/p90, relief p50/p90, and roughness mean/p90. Each metric uses:

```text
similarity = exp(-0.5 * (difference / tolerance)^2)
```

Weights are normalized across valid metrics. Versioned weights, tolerances, and rationales are in `backend/app/data/similarity.v2.json`.

## Quality gates

A summary can be `real_processed` only when it has a manifest, input SHA-256, AOI/version, processing run, methodology version, source URL, and at least 0.90 valid coverage. Processing rejects missing CRS, non-metric Mars projections, invalid resolutions, checksum changes, empty AOI intersections, and site/AOI mismatches. It warns about excessive nodata and slopes above 60 degrees. Comparison compatibility reports AOI-scale, target-resolution, and methodology matches separately.

## Reproducibility - PowerShell

From the repository root:

```powershell
cd backend
uv python install 3.12
uv venv --python 3.12 .venv-geo
uv pip install --python .venv-geo\Scripts\python.exe -r requirements-terrain.txt
```

Acquire, inspect, and process Jezero:

```powershell
.venv-geo\Scripts\python.exe -m app.scripts.acquire_dataset --source-id mars-jezero-ctx-dem
.venv-geo\Scripts\python.exe -m app.scripts.inspect_dem data\raw\M20_JezeroCrater_CTXDEM_20m.tif
.venv-geo\Scripts\python.exe -m app.scripts.process_site --site-id mars-jezero --aoi-id mars-jezero-aoi-v1 --source-id mars-jezero-ctx-dem --input data\raw\M20_JezeroCrater_CTXDEM_20m.tif --target-resolution-m 60
```

Acquire and process Atacama using the token stored in `backend\.env`:

```powershell
.venv-geo\Scripts\python.exe -m app.scripts.acquire_dataset --source-id earth-atacama-srtmgl1
.venv-geo\Scripts\python.exe -m app.scripts.process_site --site-id earth-atacama --aoi-id earth-atacama-aoi-v1 --source-id earth-atacama-srtmgl1 --input data\raw\S25W070.hgt --target-resolution-m 60
.venv-geo\Scripts\python.exe -m app.scripts.validate_comparison --reference mars-jezero --candidate earth-atacama
```

Process the remaining Phase 3 SRTM candidates with the same authenticated session:

```powershell
.venv-geo\Scripts\python.exe -m app.scripts.acquire_dataset --source-id earth-upper-mustang-srtmgl1
.venv-geo\Scripts\python.exe -m app.scripts.process_site --site-id earth-upper-mustang --aoi-id earth-upper-mustang-aoi-v1 --source-id earth-upper-mustang-srtmgl1 --input data\raw\N29E083.hgt --target-resolution-m 60
.venv-geo\Scripts\python.exe -m app.scripts.acquire_dataset --source-id earth-ladakh-srtmgl1
.venv-geo\Scripts\python.exe -m app.scripts.process_site --site-id earth-ladakh --aoi-id earth-ladakh-aoi-v1 --source-id earth-ladakh-srtmgl1 --input data\raw\N34E077.hgt --target-resolution-m 60
```

If an AOI intersects multiple tiles, use the `data\interim\<source-id>.mosaic.tif` path reported by `acquire_dataset` as `--input`. Successful quality validation automatically makes the processed summary authoritative to the API; no catalog edit is needed.

Alternatively set both `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in the current terminal. Never save credentials in tracked files. If downloading manually, place the archive at `backend/data/raw/S25W070.SRTMGL1.hgt.zip`, extract `S25W070.hgt` beside it, then run `acquire_dataset` to checksum/inspect the registered archive before processing.

## Run the application

Backend:

```powershell
cd backend
.venv-geo\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend in another terminal:

```powershell
cd frontend
Copy-Item .env.example .env.local -Force
npm.cmd ci
npm.cmd run dev
```

Open <http://localhost:3000>; API documentation is at <http://localhost:8000/docs>.

## API additions

- `GET /api/sites/{site_id}/aoi`
- `GET /api/sites/{site_id}/terrain`
- `GET /api/sources` and `/api/sources/{source_id}`
- `GET /api/processing-runs/{run_id}`
- `POST /api/discover` remains request-compatible and now adds compatibility, provenance, processing quality, and preview/real classification.

## Tests and build

```powershell
cd backend
.venv-geo\Scripts\python.exe -m pytest -q

cd ..\frontend
npm.cmd run lint
npm.cmd exec tsc -- --noEmit
npm.cmd run build
npm.cmd run test:e2e
```

Unit and browser tests are offline. Browser tests start or reuse the API on port 8000 and frontend on port 3000. Acquisition is deliberately separate because it needs Earthdata authentication.

## Adding another Earth site

Add a validated source manifest and versioned GeoJSON AOI, acquire or place the raster under ignored `backend/data/raw/`, run `process_site` with a 60 m target, inspect warnings, and add the summary only after quality gates pass. No API or frontend code change is required for the summary loader; map/site catalog metadata still needs the new site entry.

## Troubleshooting

- Rasterio did not provide a wheel for the machine's Python 3.14 environment, so the reproducible geospatial environment uses Python 3.12.
- A `401`, `403`, or credentials message for SRTM means Earthdata credentials are absent or unauthorized.
- The acquisition workflow reads `EARTHDATA_TOKEN` from `backend\.env` as dotenv data. The token is never included in errors or logs.
- A checksum mismatch means the source file changed or the wrong file is being processed; do not bypass it.
- Empty AOI errors usually indicate a wrong tile, longitude convention, or CRS.

## Scientific limitations

This score measures terrain similarity within equal-scale elevation-model windows. It does not measure atmosphere, gravity, radiation, geology, temperature, water/ice, accessibility, operational safety, or habitability. Even the current real SRTM comparisons are partial terrain analogies, not total planetary-similarity or mission-suitability claims.
