import argparse
import json
from pathlib import Path

from app.models.schemas import TerrainFeatureSummary
from app.services.geospatial_service import GEO_DATA


def load(site_id: str) -> TerrainFeatureSummary:
    path = GEO_DATA / "processed" / f"{site_id}.terrain.json"
    if not path.exists(): raise SystemExit(f"Missing processed summary: {path}")
    return TerrainFeatureSummary.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate two processed terrain summaries for comparison")
    parser.add_argument("--reference", required=True); parser.add_argument("--candidate", required=True)
    args = parser.parse_args(); reference, candidate = load(args.reference), load(args.candidate)
    resolution_match = reference.resolution_m == candidate.resolution_m
    scale_match = reference.analysis_width_m == candidate.analysis_width_m and reference.analysis_height_m == candidate.analysis_height_m
    method_match = reference.calculation_metadata.get("methodology_version") == candidate.calculation_metadata.get("methodology_version")
    real_pair = reference.data_status.value == candidate.data_status.value == "real_processed"
    warnings = []
    if not resolution_match: warnings.append("Target resolutions differ")
    if not scale_match: warnings.append("AOI physical dimensions differ")
    if not method_match: warnings.append("Methodology versions differ")
    if not real_pair: warnings.append("Both inputs must be real_processed; real and demo results are never mixed")
    print(json.dumps({"compatible": resolution_match and scale_match and method_match and real_pair, "aoi_scale_match": scale_match, "resolution_match": resolution_match, "methodology_match": method_match, "reference_resolution_m": reference.resolution_m, "candidate_resolution_m": candidate.resolution_m, "warnings": warnings}, indent=2))


if __name__ == "__main__": main()
