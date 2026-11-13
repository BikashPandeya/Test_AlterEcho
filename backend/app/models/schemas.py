from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class DataStatus(str, Enum):
    real_processed = "real_processed"
    demo_fixture = "demo_fixture"
    metadata_only = "metadata_only"
    unavailable = "unavailable"


class Body(str, Enum):
    earth = "earth"
    mars = "mars"
    moon = "moon"


class Planet(BaseModel):
    id: Body
    name: str
    description: str
    status: str
    supported_capabilities: list[str]
    default_view: dict[str, Any]


class SourceReference(BaseModel):
    id: str
    title: str
    url: str
    role: str


class Site(BaseModel):
    id: str
    name: str
    body: Body
    country_or_region: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    short_description: str
    analog_type: str
    relevant_characteristics: list[str]
    known_limitations: list[str]
    source_references: list[str]
    data_status: DataStatus
    available_metrics: list[str]
    thumbnail_url: str | None = None
    map_display: dict[str, Any]


class TerrainFeatureSummary(BaseModel):
    site_id: str
    slope_p50_deg: float | None = None
    slope_p90_deg: float | None = None
    local_relief_m: float | None = None
    roughness_index: float | None = None
    elevation_min_m: float | None = None
    elevation_max_m: float | None = None
    elevation_mean_m: float | None = None
    elevation_std_m: float | None = None
    elevation_p10_m: float | None = None
    elevation_p50_m: float | None = None
    elevation_p90_m: float | None = None
    slope_mean_deg: float | None = None
    slope_max_deg: float | None = None
    local_relief_mean_m: float | None = None
    local_relief_p50_m: float | None = None
    local_relief_p90_m: float | None = None
    roughness_mean: float | None = None
    roughness_p90: float | None = None
    valid_coverage_fraction: float = Field(ge=0, le=1)
    resolution_m: float | None = Field(default=None, gt=0)
    projection: str | None = None
    calculation_metadata: dict[str, Any]
    data_source: str
    data_status: DataStatus
    aoi_id: str | None = None
    processing_run_id: str | None = None
    analysis_width_m: float | None = None
    analysis_height_m: float | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def real_data_requires_traceability(self):
        if self.data_status == DataStatus.real_processed:
            required = {"source_checksum", "aoi_id", "processing_run_id", "methodology_version"}
            missing = required - set(self.provenance)
            if missing:
                raise ValueError(f"real_processed requires provenance fields: {', '.join(sorted(missing))}")
        return self


class SourceManifest(BaseModel):
    source_id: str
    title: str
    planetary_body: str
    provider: str
    mission: str | None
    instrument: str | None
    product_name: str
    product_version: str | None
    source_page_url: str
    download_url: str | None
    doi: str | None
    access_date: str | None
    license_or_use_constraints: str | None
    native_resolution: str | list[float] | None
    native_crs: str | None
    native_bounds: list[float] | None
    native_nodata: float | None
    file_size: int | None
    filename: str
    sha256_checksum: str | None
    citation_text: str
    processing_status: str
    notes: str | None
    extracted_filename: str | None = None
    extracted_sha256_checksum: str | None = None
    aoi_id: str | None = None
    tiles: list[dict[str, Any]] = Field(default_factory=list)
    mosaic_filename: str | None = None
    mosaic_sha256_checksum: str | None = None


class AOIRecord(BaseModel):
    aoi_id: str
    site_id: str
    version: str
    planetary_body: str
    center_latitude: float
    center_longitude: float
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    selection_rationale: str
    intended_analog_characteristics: list[str]
    known_limitations: list[str]
    creation_method: str
    source_references: list[str]
    geometry: dict[str, Any]


class Compatibility(BaseModel):
    compatible: bool
    aoi_scale_match: bool
    resolution_match: bool
    methodology_match: bool
    reference_resolution_m: float | None
    candidate_resolution_m: float | None
    warnings: list[str] = Field(default_factory=list)


class ProcessingRun(BaseModel):
    processing_run_id: str
    timestamp: datetime
    site_id: str
    source_id: str
    source_checksum: str
    aoi_version: str
    methodology_version: str
    software_version: str
    native_resolution: list[float]
    target_resolution: float
    source_crs: str
    processing_crs: str
    resampling_method: str
    nodata_handling: str
    requested_analysis_window_m: list[float]
    actual_analysis_window_m: list[float]
    grid_dimensions: list[int]
    metric_configuration: dict[str, Any]
    output_summary: str
    output_checksum: str
    quality_passed: bool
    warnings: list[str]


class DiscoverRequest(BaseModel):
    reference_site_id: str = "mars-jezero"
    candidate_site_ids: list[str] = Field(min_length=1, max_length=20)
    weights: dict[str, float] | None = None

    @field_validator("candidate_site_ids")
    @classmethod
    def unique_candidates(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("candidate_site_ids must not contain duplicates")
        return value

    @field_validator("weights")
    @classmethod
    def valid_weights(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is None:
            return value
        if any(weight < 0 for weight in value.values()):
            raise ValueError("weights cannot be negative")
        if not any(weight > 0 for weight in value.values()):
            raise ValueError("weights must contain a positive value")
        return value


class MetricComparison(BaseModel):
    metric: str
    reference_value: float
    candidate_value: float
    tolerance: float
    normalized_weight: float
    similarity: float = Field(ge=0, le=1)


class ComparisonResult(BaseModel):
    request_id: str
    reference_site: Site
    candidate_site: Site
    overall_similarity: float | None
    display_percentage: float | None
    rankability: str
    metric_similarities: list[MetricComparison]
    available_metrics: list[str]
    missing_metrics: list[str]
    explanation: str
    limitations: list[str]
    provenance: dict[str, Any]
    data_status: DataStatus
    methodology_version: str
    generated_at: datetime
    compatibility: Compatibility | None = None
    quality: dict[str, Any] = Field(default_factory=dict)
    ranking_scope: str = "preview_only"
    reference_data_status: DataStatus | None = None
    candidate_data_status: DataStatus | None = None
    comparison_classification: str = "preview"
    processing_run_ids: dict[str, str | None] = Field(default_factory=dict)


class DiscoverResponse(BaseModel):
    request_id: str
    reference_site_id: str
    results: list[ComparisonResult]
    methodology_version: str
    data_mode: str
    generated_at: datetime
    ranking_scope: str = "preview_only"
    real_results: list[ComparisonResult] = Field(default_factory=list)
    preview_results: list[ComparisonResult] = Field(default_factory=list)

