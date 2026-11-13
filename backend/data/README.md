# TerraLuna geospatial data

- `manifests/` records source identity, access, checksums, and inspected native metadata.
- `aoi/` contains versioned equal-scale study windows.
- `processed/` contains small terrain summaries and processing reports safe for version control.
- `sources/` may hold small provider metadata or acquisition receipts.
- `raw/`, `interim/`, and `cache/` are local-only and ignored because source rasters can be large.

The two Phase 2 AOIs request 10,000 m square windows. A 60 m grid produces 167 by 167 cells and an actual analyzed extent of 10,020 m square; both requested and actual extents are recorded.

