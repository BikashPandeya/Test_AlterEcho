import pytest

from app.models.schemas import DataStatus, TerrainFeatureSummary
from app.services.similarity_service import SimilarityInputError, compare_features


def summary(**overrides):
    values = {"site_id": "test", "slope_p50_deg": 5.0, "slope_p90_deg": 10.0, "local_relief_m": 100.0, "roughness_index": None, "valid_coverage_fraction": 1.0, "resolution_m": 30.0, "projection": "EPSG:32645", "calculation_metadata": {}, "data_source": "test fixture", "data_status": DataStatus.demo_fixture}
    values.update(overrides)
    return TerrainFeatureSummary(**values)


def test_identical_is_maximum_and_difference_lowers_score():
    reference = summary()
    identical = compare_features(reference, summary())
    different = compare_features(reference, summary(slope_p50_deg=15, slope_p90_deg=30, local_relief_m=500))
    assert identical["overall_similarity"] == pytest.approx(1.0)
    assert different["overall_similarity"] < identical["overall_similarity"]


def test_all_required_missing_is_not_rankable():
    result = compare_features(summary(), summary(slope_p50_deg=None, slope_p90_deg=None, local_relief_m=None))
    assert result["rankability"] == "not_rankable"
    assert result["overall_similarity"] is None


def test_missing_optional_metric_is_reported():
    result = compare_features(summary(roughness_index=0.2), summary(roughness_index=None), {"slope_p50_deg": 0.5, "roughness_index": 0.5})
    assert result["rankability"] == "not_rankable"
    assert result["missing_metrics"] == ["roughness_index"]


def test_low_coverage_is_not_rankable():
    result = compare_features(summary(), summary(valid_coverage_fraction=0.5))
    assert result["rankability"] == "not_rankable"
    assert result["overall_similarity"] is None

