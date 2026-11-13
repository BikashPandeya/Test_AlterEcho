import argparse
import json

from app.services.geospatial_service import process_site


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop, harmonize, validate, and summarize one site DEM")
    parser.add_argument("--site-id", required=True); parser.add_argument("--aoi-id", required=True)
    parser.add_argument("--source-id", required=True); parser.add_argument("--input", required=True)
    parser.add_argument("--target-resolution-m", type=float, default=60.0)
    args = parser.parse_args()
    summary, report = process_site(args.input, args.site_id, args.aoi_id, args.source_id, args.target_resolution_m)
    print(json.dumps({"site_id": summary.site_id, "data_status": summary.data_status, "valid_coverage_fraction": summary.valid_coverage_fraction, "processing_run_id": report["processing_run_id"], "warnings": report["warnings"]}, indent=2))


if __name__ == "__main__": main()

