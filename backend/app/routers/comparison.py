from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import Compatibility, ComparisonResult, DataStatus, DiscoverRequest, DiscoverResponse
from app.services.catalog_service import get_feature_summary, get_processed_summary, get_site
from app.services.explanation_service import explain
from app.services.similarity_service import CONFIG, CONFIG_V2, SimilarityInputError, compare_features


router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest):
    reference_site = get_site(request.reference_site_id)
    if not reference_site:
        raise HTTPException(status_code=404, detail={"code": "reference_not_found", "message": f"Unknown reference site ID: {request.reference_site_id}"})
    reference_fixture = get_feature_summary(request.reference_site_id)
    reference_processed = get_processed_summary(request.reference_site_id)
    if not reference_fixture and not reference_processed:
        raise HTTPException(status_code=422, detail={"code": "reference_features_unavailable", "message": "Reference site has no terrain feature summary"})

    unknown = [site_id for site_id in request.candidate_site_ids if not get_site(site_id)]
    if unknown:
        raise HTTPException(status_code=404, detail={"code": "candidate_not_found", "message": f"Unknown candidate site IDs: {', '.join(unknown)}"})

    request_id = str(uuid4())
    generated_at = datetime.now(timezone.utc)
    results = []
    for candidate_id in request.candidate_site_ids:
        candidate = get_site(candidate_id)
        candidate_fixture = get_feature_summary(candidate_id)
        candidate_processed = get_processed_summary(candidate_id)
        real_pair = bool(reference_processed and candidate_processed and reference_processed.data_status == candidate_processed.data_status == DataStatus.real_processed)
        use_v2 = real_pair and request.weights is None
        reference_features = reference_processed if real_pair else reference_fixture
        candidate_features = candidate_processed if real_pair else candidate_fixture
        active_config = CONFIG_V2 if use_v2 else CONFIG
        compatibility_warnings: list[str] = []
        if not real_pair and reference_processed:
            compatibility_warnings.append("A real Jezero summary exists, but this preview uses the matched demo-fixture pair; real and demo terrain values were not mixed.")
        if not candidate_processed:
            compatibility_warnings.append("Candidate has no validated real-processed terrain summary.")
        if candidate_features is None:
            comparison = {"overall_similarity": None, "rankability": "not_rankable", "metric_similarities": [], "available_metrics": [], "missing_metrics": list((request.weights or active_config["default_weights"]).keys()), "coverage_ok": False}
        else:
            try:
                comparison = compare_features(reference_features, candidate_features, request.weights, active_config)
            except SimilarityInputError as error:
                raise HTTPException(status_code=422, detail={"code": "invalid_comparison", "message": str(error)}) from error
        explanation, limitations = explain(candidate, comparison["metric_similarities"], comparison["rankability"] == "rankable", comparison["coverage_ok"])
        if not real_pair:
            limitations = [*limitations, "The demo fixture values are synthetic and cannot support scientific ranking conclusions."]
        score = comparison["overall_similarity"]
        resolution_match = bool(reference_features and candidate_features and reference_features.resolution_m == candidate_features.resolution_m)
        scale_match = bool(real_pair and reference_features.analysis_width_m == candidate_features.analysis_width_m and reference_features.analysis_height_m == candidate_features.analysis_height_m) if real_pair else True
        method_match = bool(reference_features and candidate_features and reference_features.calculation_metadata.get("methodology_version") == candidate_features.calculation_metadata.get("methodology_version"))
        compatible = comparison["rankability"] == "rankable" and resolution_match and scale_match and method_match
        methodology_version = active_config["methodology_version"]
        results.append(ComparisonResult(
            request_id=request_id, reference_site=reference_site, candidate_site=candidate,
            overall_similarity=score, display_percentage=round(score * 100, 1) if score is not None else None,
            rankability=comparison["rankability"], metric_similarities=comparison["metric_similarities"],
            available_metrics=comparison["available_metrics"], missing_metrics=comparison["missing_metrics"],
            explanation=explanation, limitations=limitations,
            provenance={"reference_feature_source": reference_features.data_source if reference_features else None, "candidate_feature_source": candidate_features.data_source if candidate_features else None, "reference": reference_features.provenance if real_pair else {}, "candidate": candidate_features.provenance if real_pair and candidate_features else {}, "notice": "Comparison generated from processed elevation datasets." if real_pair else "Synthetic demo fixtures; not NASA-derived terrain conclusions."},
            data_status=DataStatus.real_processed if real_pair else (DataStatus.demo_fixture if candidate_features else DataStatus.metadata_only),
            methodology_version=methodology_version, generated_at=generated_at,
            compatibility=Compatibility(compatible=compatible, aoi_scale_match=scale_match, resolution_match=resolution_match, methodology_match=method_match, reference_resolution_m=reference_features.resolution_m if reference_features else None, candidate_resolution_m=candidate_features.resolution_m if candidate_features else None, warnings=compatibility_warnings),
            quality={"reference": reference_features.quality if real_pair else {}, "candidate": candidate_features.quality if real_pair and candidate_features else {}, "classification": "real_comparison" if real_pair else "preview"},
            ranking_scope="real_only" if real_pair else "preview_only",
            reference_data_status=reference_features.data_status if reference_features else DataStatus.unavailable,
            candidate_data_status=candidate_features.data_status if candidate_features else candidate.data_status,
            comparison_classification="real_comparison" if real_pair else ("preview" if candidate_features else "not_rankable_metadata"),
            processing_run_ids={"reference": reference_features.processing_run_id if real_pair and reference_features else None, "candidate": candidate_features.processing_run_id if real_pair and candidate_features else None},
        ))
    real_results = sorted((item for item in results if item.ranking_scope == "real_only"), key=lambda item: item.overall_similarity if item.overall_similarity is not None else -1, reverse=True)
    preview_results = sorted((item for item in results if item.ranking_scope == "preview_only"), key=lambda item: item.overall_similarity if item.overall_similarity is not None else -1, reverse=True)
    results = real_results + preview_results
    response_method = results[0].methodology_version if results and len({item.methodology_version for item in results}) == 1 else settings.methodology_version
    return DiscoverResponse(request_id=request_id, reference_site_id=request.reference_site_id, results=results, methodology_version=response_method, data_mode="mixed" if real_results and preview_results else ("real" if real_results else "demo"), generated_at=generated_at, ranking_scope="real_only" if real_results else "preview_only", real_results=real_results, preview_results=preview_results)

