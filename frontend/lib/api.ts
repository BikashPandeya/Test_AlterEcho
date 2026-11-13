export type DataStatus = "real_processed" | "demo_fixture" | "metadata_only" | "unavailable";

export interface Site {
  id: string; name: string; body: "earth" | "mars" | "moon";
  country_or_region: string; latitude: number; longitude: number;
  short_description: string; analog_type: string;
  relevant_characteristics: string[]; known_limitations: string[];
  source_references: string[]; data_status: DataStatus;
  available_metrics: string[]; thumbnail_url: string | null;
  map_display: Record<string, unknown>;
}
export interface HealthResponse { status: string; application_version: string; methodology_version: string; data_mode: "real" | "mixed" | "demo" | "unavailable"; data_counts: { real_processed_sites: number; demo_fixture_sites: number; metadata_only_sites: number; unavailable_sites: number; rankable_real_candidates: number }; timestamp: string; }
export interface MetricComparison { metric: string; reference_value: number; candidate_value: number; tolerance: number; normalized_weight: number; similarity: number; }
export interface ComparisonResult {
  request_id: string; reference_site: Site; candidate_site: Site; overall_similarity: number | null;
  display_percentage: number | null; rankability: "rankable" | "not_rankable"; metric_similarities: MetricComparison[];
  available_metrics: string[]; missing_metrics: string[]; explanation: string; limitations: string[];
  provenance: Record<string, unknown>; data_status: DataStatus; methodology_version: string; generated_at: string;
  compatibility: { compatible: boolean; aoi_scale_match: boolean; resolution_match: boolean; methodology_match: boolean; reference_resolution_m: number | null; candidate_resolution_m: number | null; warnings: string[] } | null;
  quality: Record<string, unknown>;
  ranking_scope: "real_only" | "preview_only";
  reference_data_status: DataStatus;
  candidate_data_status: DataStatus;
  comparison_classification: "real_comparison" | "preview" | "not_rankable_metadata";
  processing_run_ids: { reference: string | null; candidate: string | null };
}
export interface DiscoverResponse { request_id: string; reference_site_id: string; results: ComparisonResult[]; real_results: ComparisonResult[]; preview_results: ComparisonResult[]; ranking_scope: "real_only" | "preview_only"; methodology_version: string; data_mode: string; generated_at: string; }
export interface AoiFeature { type: "Feature"; id?: string; properties: { aoi_id: string; site_id: string; version: string; planetary_body: string; width_m: number; height_m: number; [key: string]: unknown }; geometry: { type: "Polygon"; coordinates: number[][][] }; }
export interface TerrainSummary { site_id: string; data_status: DataStatus; resolution_m: number | null; valid_coverage_fraction: number; aoi_id: string | null; processing_run_id: string | null; analysis_width_m: number | null; analysis_height_m: number | null; calculation_metadata: Record<string, unknown>; provenance: Record<string, unknown>; quality: Record<string, unknown>; [key: string]: unknown; }
export interface SourceManifest { source_id: string; title: string; provider: string; mission: string | null; instrument: string | null; native_resolution: string | number[] | null; source_page_url: string; processing_status: string; access_date: string | null; }

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
export class ApiError extends Error { constructor(message: string, public readonly status?: number) { super(message); } }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers }, signal: init?.signal ?? controller.signal });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new ApiError(payload?.detail?.message ?? payload?.error?.message ?? `Backend request failed (${response.status})`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new ApiError("Backend request timed out");
    throw new ApiError("Backend unavailable");
  } finally { window.clearTimeout(timeout); }
}

const requestCache = new Map<string, Promise<unknown>>();
function cachedRequest<T>(path: string): Promise<T> {
  const existing = requestCache.get(path) as Promise<T> | undefined;
  if (existing) return existing;
  const pending = request<T>(path).catch((error) => { requestCache.delete(path); throw error; });
  requestCache.set(path, pending); return pending;
}

export const api = {
  health: () => cachedRequest<HealthResponse>("/api/health"),
  sites: (body?: Site["body"]) => cachedRequest<Site[]>(`/api/sites${body ? `?body=${body}` : ""}`),
  discover: (candidateSiteIds: string[]) => request<DiscoverResponse>("/api/discover", { method: "POST", body: JSON.stringify({ reference_site_id: "mars-jezero", candidate_site_ids: candidateSiteIds }) }),
  aoi: (siteId: string) => cachedRequest<AoiFeature>(`/api/sites/${siteId}/aoi`),
  terrain: (siteId: string, signal?: AbortSignal) => signal
    ? request<TerrainSummary>(`/api/sites/${siteId}/terrain`, { signal })
    : cachedRequest<TerrainSummary>(`/api/sites/${siteId}/terrain`),
  sources: () => cachedRequest<SourceManifest[]>("/api/sources"),
};

