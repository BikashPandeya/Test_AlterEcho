import json
from math import exp
from pathlib import Path

from app.models.schemas import Compatibility, DataStatus, MetricComparison, TerrainFeatureSummary


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CONFIG = json.loads((DATA_DIR / "similarity.v1.json").read_text(encoding="utf-8"))
CONFIG_V2 = json.loads((DATA_DIR / "similarity.v2.json").read_text(encoding="utf-8"))


class SimilarityInputError(ValueError):
    pass


def check_compatibility(reference: TerrainFeatureSummary, candidate: TerrainFeatureSummary, require_real: bool = True) -> Compatibility:
    warnings: list[str] = []
    resolution_match = reference.resolution_m is not None and candidate.resolution_m is not None and abs(reference.resolution_m - candidate.resolution_m) < 1e-6
    aoi_scale_match = reference.analysis_width_m == candidate.analysis_width_m and reference.analysis_height_m == candidate.analysis_height_m and reference.analysis_width_m is not None
    methodology_match = reference.calculation_metadata.get("methodology_version") == candidate.calculation_metadata.get("methodology_version") and reference.calculation_metadata.get("methodology_version") is not None
    real_pair = reference.data_status == candidate.data_status == DataStatus.real_processed
    if not resolution_match: warnings.append("Target resolutions differ")
    if not aoi_scale_match: warnings.append("AOI physical dimensions differ or are unavailable")
    if not methodology_match: warnings.append("Methodology versions differ or are unavailable")
    if require_real and not real_pair: warnings.append("Both inputs must be real_processed; real and demo terrain values are never mixed")
    return Compatibility(compatible=resolution_match and aoi_scale_match and methodology_match and (real_pair or not require_real), aoi_scale_match=aoi_scale_match, resolution_match=resolution_match, methodology_match=methodology_match, reference_resolution_m=reference.resolution_m, candidate_resolution_m=candidate.resolution_m, warnings=warnings)


def compare_features(
    reference: TerrainFeatureSummary,
    candidate: TerrainFeatureSummary,
    requested_weights: dict[str, float] | None = None,
    config: dict | None = None,
) -> dict:
    active_config = config or CONFIG
    weights = requested_weights or active_config["default_weights"]
    unknown = set(weights) - set(active_config["tolerances"])
    if unknown:
        raise SimilarityInputError(f"Unsupported metrics: {', '.join(sorted(unknown))}")
    if any(weight < 0 for weight in weights.values()):
        raise SimilarityInputError("Weights cannot be negative")

    metrics: list[tuple[str, float, float, float, float]] = []
    missing: list[str] = []
    for metric, weight in weights.items():
        ref_value = getattr(reference, metric, None)
        candidate_value = getattr(candidate, metric, None)
        if weight <= 0:
            continue
        if ref_value is None or candidate_value is None:
            missing.append(metric)
            continue
        tolerance_config = active_config["tolerances"][metric]
        tolerance = float(tolerance_config["value"] if isinstance(tolerance_config, dict) else tolerance_config)
        similarity = exp(-0.5 * ((candidate_value - ref_value) / tolerance) ** 2)
        metrics.append((metric, ref_value, candidate_value, weight, similarity))

    total_weight = sum(metric[3] for metric in metrics)
    if total_weight <= 0:
        return {
            "overall_similarity": None,
            "rankability": "not_rankable",
            "metric_similarities": [],
            "available_metrics": [],
            "missing_metrics": sorted(set(missing)),
            "coverage_ok": min(reference.valid_coverage_fraction, candidate.valid_coverage_fraction) >= active_config["minimum_valid_coverage_fraction"],
        }

    coverage_ok = min(reference.valid_coverage_fraction, candidate.valid_coverage_fraction) >= active_config["minimum_valid_coverage_fraction"]
    rankable = len(metrics) >= active_config["minimum_usable_metrics"] and coverage_ok
    details = [
        MetricComparison(
            metric=name,
            reference_value=ref,
            candidate_value=candidate_value,
            tolerance=float(active_config["tolerances"][name]["value"] if isinstance(active_config["tolerances"][name], dict) else active_config["tolerances"][name]),
            normalized_weight=weight / total_weight,
            similarity=similarity,
        )
        for name, ref, candidate_value, weight, similarity in metrics
    ]
    overall = sum(item.similarity * item.normalized_weight for item in details) if rankable else None
    return {
        "overall_similarity": overall,
        "rankability": "rankable" if rankable else "not_rankable",
        "metric_similarities": details,
        "available_metrics": [item.metric for item in details],
        "missing_metrics": sorted(set(missing)),
        "coverage_ok": coverage_ok,
    }

