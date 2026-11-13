# TerraLuna AI backend

Welcome! This is the FastAPI side of TerraLuna AI. It provides the catalog of planetary bodies and terrain sites, comparison endpoints for the frontend, and a separate toolchain for processing elevation data.

The easiest way to understand the backend is to follow one request from the moment the server starts.

## The story of a request

1. **The server starts in `app/main.py`.** FastAPI is created there, CORS is enabled for the local frontend, and the health, catalog, comparison, and geospatial routers are registered under `/api`.
2. **The frontend (or you) calls an endpoint.** For example, `GET /api/sites` asks for the catalog, while `POST /api/discover` asks for terrain comparisons.
3. **A router handles the URL.** Files in `app/routers/` validate the request shape, call the relevant service, and turn missing or invalid input into an HTTP error.
4. **A service does the work.** Services load catalog or terrain data, calculate comparisons, or assemble explanations. The API does not keep its catalog and scientific settings hard-coded in route functions.
5. **Pydantic checks the data shape.** The models in `app/models/s.py` describe accepted requests and returned objects.
6. **FastAPI sends JSON back.** OpenAPI documentation and a testable API are available at `/docs`.

In short:

```text
Browser or API client
    -> app/main.py
    -> app/routers/
    -> app/services/
    -> app/data/ and/or backend/data/
    -> validated JSON response
```

## Run it after cloning

From a PowerShell terminal at the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Then open:

- API landing response: <http://localhost:8000/>
- Interactive API docs: <http://localhost:8000/docs>
- Health information: <http://localhost:8000/api/health>

The regular API and demo comparisons use the packages in `requirements.txt`; they do not need Rasterio or the original DEM files. Python 3.12 is recommended, especially if you also plan to install the optional geospatial dependencies.

To stop the server, press **Ctrl+C** in the terminal. To run the backend tests from `backend/`:

```powershell
python -m pytest -q
```

## Where to look in the code

| Path | What it does |
| --- | --- |
| `app/main.py` | Creates the FastAPI app, installs CORS and error handlers, and mounts the routers. |
| `app/config.py` | Reads app and CORS settings from environment variables. |
| `app/routers/health.py` | Health and feature/configuration endpoints. |
| `app/routers/catalog.py` | Planet, site, and methodology endpoints. |
| `app/routers/comparison.py` | The `POST /api/discover` workflow: checks requested sites, chooses the appropriate feature data, compares candidates, and builds the response. |
| `app/routers/geospatial.py` | Endpoints for AOIs, terrain summaries, source manifests, and processing runs. |
| `app/models/s.py` | Pydantic models for sites, requests, terrain summaries, provenance, comparisons, and API responses. |
| `app/services/catalog_service.py` | Loads and filters the catalog JSON and finds any processed terrain summary for a site. |
| `app/services/similarity_service.py` | Applies the configured metric weights and tolerances to produce terrain similarity scores. |
| `app/services/explanation_service.py` | Turns comparison metrics and rankability into a short explanation and limitations. |
| `app/services/terrain_service.py` | Computes elevation, slope, local-relief, roughness, coverage, and quality summaries from elevation arrays. |
| `app/services/geospatial_service.py` | Loads AOIs and manifests; handles DEM reprojection, AOI grid creation, processing records, and saved summaries. |
| `app/services/srtm_service.py` | Calculates SRTM tile names and mosaics tiles when an AOI crosses tile boundaries. |
| `app/scripts/` | Command-line tools for acquiring, inspecting, processing, and validating elevation data. |
| `tests/` | API, comparison, terrain, and data-processing tests. |

### The API routes

All application endpoints are grouped under `/api`:

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Reports whether the API is online and summarizes the available data statuses. |
| `GET /api/config` | Describes enabled bodies/features and the current data mode. |
| `GET /api/planets` | Returns the supported planetary-body catalog. |
| `GET /api/sites` | Lists sites; optional filters include `body`, `data_status`, and `analog_type`. |
| `GET /api/sites/{site_id}` | Returns one site. |
| `GET /api/methodology` | Describes the comparison metrics, formula, and limitations. |
| `POST /api/discover` | Compares one reference site with one or more candidate sites. |
| `GET /api/sites/{site_id}/aoi` | Returns the site's GeoJSON area of interest, if registered. |
| `GET /api/sites/{site_id}/terrain` | Returns a processed summary or demo feature summary. |
| `GET /api/sources` and `GET /api/sources/{source_id}` | Returns source provenance records. |
| `GET /api/processing-runs/{run_id}` | Returns the report for a processing run. |

For example, the discovery request body can look like this:

```json
{
  "reference_site_id": "mars-jezero",
  "candidate_site_ids": ["earth-atacama", "earth-upper-mustang"]
}
```

You can send it to `POST http://localhost:8000/api/discover`. The response separates real-data comparisons from previews. Synthetic demo values are useful for exercising the interface, but they are not scientific results; real and demo terrain values are never combined into one comparison.

## The two JSON data folders

There are two different JSON areas, with different jobs. This distinction is useful when adding or debugging data.

### `app/data/`: catalog and comparison settings

These are small, checked-in application inputs read by `catalog_service.py` and `similarity_service.py`:

- `planets.json` describes supported planetary bodies.
- `sites.json` describes catalog sites and their display/catalog metadata.
- `sources.json` contains source references used by the catalog.
- `comparisons.demo.json` contains **synthetic demo terrain features** for previews where a validated processed summary is not available.
- `similarity.v1.json` and `similarity.v2.json` contain versioned metric tolerances, weights, and minimum coverage/metric requirements. Keep comparison settings here rather than putting scientific constants in router code.

### `data/`: geospatial provenance and generated outputs

This folder is next to `app/` at the backend root (that is, `backend/data/`):

- `manifests/` stores JSON records for source datasets, including source identity and available checksum/inspection metadata.
- `aoi/` stores versioned GeoJSON areas of interest (AOIs): the study windows used to select and compare terrain.
- `processed/` stores small, runtime-readable `*.terrain.json` summaries and `*.processing.json` run reports. The API can use a validated processed summary without needing the original raster.
- `raw/` is for downloaded or locally supplied source rasters; `interim/` is for intermediate rasters such as mosaics and harmonized DEMs. These can be large and are intended to stay out of version control.
- `README.md` in this folder explains the geospatial data layout and the requested-versus-actual AOI grid size.

The data path for a real DEM is:

```text
source manifest + AOI
    -> acquire/inspect source raster
    -> reproject and resample to the analysis grid
    -> calculate terrain metrics and quality/provenance
    -> data/processed/<site>.terrain.json + <run-id>.processing.json
    -> API serves the processed summary
```

An AOI requests a physical study area and a target resolution. Since the requested dimensions may not divide evenly into the pixel size, the processing report records both the requested and actual grid extents.

## How terrain comparisons work

For each candidate, the comparison workflow finds the reference and candidate feature summaries, then compares the configured terrain metrics. The score for each metric uses a Gaussian-style similarity:

```text
similarity = exp(-0.5 * (difference / tolerance)^2)
```

The configured metric weights are normalized across the available metrics. A comparison is only rankable when enough metrics and valid coverage are available. The response includes the score, metric details, coverage/rankability, provenance where applicable, compatibility warnings, and scientific limitations.

Elevation statistics can describe a site, but absolute elevation is not used as a cross-planet similarity metric. A terrain score is a partial terrain analogy, not a measure of habitability or overall planetary similarity.

## Optional: process real elevation data

Install the extra dependency set only if you need to inspect or process DEM rasters:

```powershell
python -m pip install -r requirements-terrain.txt
```

`requirements-terrain.txt` includes the normal backend requirements and Rasterio. The main processing command is `app.scripts.process_site`; it checks the source against its manifest, uses the selected AOI to create a metric grid, calculates terrain features, and writes the processed summary and run report.

Other useful commands, run from `backend/`:

```powershell
# Inspect a local DEM's metadata before processing
python -m app.scripts.inspect_dem path\to\elevation.tif

# Acquire/register a dataset named in data/manifests/
python -m app.scripts.acquire_dataset --source-id SOURCE_ID

# Process a DEM using a registered site, AOI, and source
python -m app.scripts.process_site --site-id SITE_ID --aoi-id AOI_ID --source-id SOURCE_ID --input path\to\elevation.tif --target-resolution-m 60

# Compare two saved processed summaries' compatibility
python -m app.scripts.validate_comparison --reference REFERENCE_SITE_ID --candidate CANDIDATE_SITE_ID
```

Replace the uppercase placeholders and example file path with IDs and paths that exist in your checkout.

Dataset acquisition may require Earthdata credentials for protected sources. Supply credentials through the environment variables expected by the acquisition script (`EARTHDATA_TOKEN`, or `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`); do not commit credentials. Raster processing is separate from running the API, and a clone can run the API without downloading any rasters.

## Environment settings

`app/config.py` reads these optional environment variables when the app starts:

- `APP_VERSION`
- `APP_ENV`
- `DATA_MODE`
- `METHODOLOGY_VERSION`
- `CORS_ORIGINS` — comma-separated allowed frontend origins; defaults to local development origins on port 3000.

Restart the server after changing environment variables so the settings are read again.
