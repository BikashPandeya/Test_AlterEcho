# TerraLuna AI backend

FastAPI serves an extensible body/site catalog and a deterministic terrain-only similarity workflow. Configuration values and tolerances live in `app/data/`; routers do not contain scientific constants.

The default `demo_fixture` mode is intentionally obvious in health and discovery responses. Rasterio is isolated in the optional `requirements-terrain.txt`, so catalog and demo comparison APIs remain runnable without GDAL/Rasterio.
