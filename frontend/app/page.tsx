"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PlanetSelector from "./components/PlanetSelector";
import { api, type AoiFeature, type ComparisonResult, type HealthResponse, type Site, type SourceManifest, type TerrainSummary } from "../lib/api";

const CandidateMap = dynamic<{ onZoomChange: (value: boolean) => void; sites: Site[]; aois: AoiFeature[]; focusedSiteId: string | null; onSelect: (site: Site) => void }>(() => import("./components/CandidateMap"), { ssr: false });
const SpaceScene = dynamic<{ onMoonClick: () => void; showOrbit: boolean }>(() => import("./components/SpaceScene"), { ssr: false });
const PlanetViewer = dynamic(() => import("./components/PlanetViewer"), { ssr: false });
type Planet = "earth" | "mars" | "moon";
const label = (value: string) => value.replaceAll("_", " ");
const dataLabel = (value: string) => ({ real_processed: "Real DEM analysis", demo_fixture: "Demo fixture", metadata_only: "Metadata only", unavailable: "Data unavailable" }[value] ?? label(value));

function ResultCard({ result, rank, onDownload }: { result: ComparisonResult; rank: number; onDownload: (result: ComparisonResult) => void }) {
  const real = result.comparison_classification === "real_comparison";
  return <article className="result-card" data-testid={`result-${result.candidate_site.id}`}>
    <header><div><p className="eyebrow">{real ? `RANK ${rank} · REAL DEM` : result.rankability === "rankable" ? "PREVIEW ONLY" : "INSUFFICIENT EVIDENCE"}</p><h3>{result.candidate_site.name}</h3><p className="result-direction">Compared with {result.reference_site.name}, Mars</p></div><div className="score-block"><span>Terrain similarity score</span><strong className="score">{result.display_percentage === null ? "Not rankable" : `${result.display_percentage}%`}</strong></div></header>
    {!real && <p className="preview-warning">Illustrative fixture values only — this is not a NASA-derived discovery.</p>}
    <div className="result-meta"><em className={`data-badge ${result.data_status}`}>{dataLabel(result.data_status)}</em><span>Method {result.methodology_version}</span></div>
    <p className={`compatibility ${result.compatibility?.compatible ? "compatible" : "preview"}`}>{result.compatibility?.compatible ? "Compatible inputs" : "Preview / compatibility limits"}</p>
    {result.compatibility?.warnings.map((warning) => <p className="warning-text" key={warning}>{warning}</p>)}
    <div className="metrics-grid">{result.metric_similarities.map((metric) => <div key={metric.metric}><span>{label(metric.metric)}</span><strong>{Math.round(metric.similarity * 100)}%</strong><small>Ref {metric.reference_value.toFixed(2)} · Candidate {metric.candidate_value.toFixed(2)}</small><i style={{ width: `${metric.similarity * 100}%` }} /></div>)}</div>
    <p>{result.explanation}</p>
    {real && <p className="run-ids">Processing runs: {result.processing_run_ids.reference} / {result.processing_run_ids.candidate}</p>}
    <p className="science-limit">This score measures terrain similarity within equal-scale elevation-model windows. It does not measure atmosphere, gravity, radiation, geology, temperature, or habitability.</p>
    <details><summary>Data & methodology</summary><ul>{result.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul><p>{String(result.provenance.notice ?? "No provenance notice")}</p><p>AOI scale and processed resolution compatibility are reported above. Source checksums and processing runs are retained in the API response.</p></details>
    <button className="download-button" type="button" onClick={() => onDownload(result)}>Download result JSON</button>
  </article>;
}

export default function Home() {
  const [activePlanet, setActivePlanet] = useState<Planet>("earth");
  const [isZoomedIn, setIsZoomedIn] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [backendError, setBackendError] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [reference, setReference] = useState<Site | null>(null);
  const [focusedCandidateId, setFocusedCandidateId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [dataFilter, setDataFilter] = useState<"all" | "real_processed" | "demo_fixture" | "metadata_only">("real_processed");
  const [aois, setAois] = useState<AoiFeature[]>([]);
  const [terrain, setTerrain] = useState<Record<string, TerrainSummary>>({});
  const [sources, setSources] = useState<SourceManifest[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonAttempted, setComparisonAttempted] = useState(false);
  const [resultsStale, setResultsStale] = useState(false);
  const [terrainError, setTerrainError] = useState<{ siteId: string; message: string } | null>(null);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.health(), api.sites("earth"), api.sites("mars")])
      .then(([healthResponse, earthSites, marsSites]) => {
        if (!active) return;
        setHealth(healthResponse); setSites(earthSites); setBackendError(false); setCatalogError(null);
        setReference(marsSites.find((site) => site.id === "mars-jezero") ?? null);
        setSelectedIds(earthSites.filter((site) => site.data_status === "real_processed").map((site) => site.id));
        setFocusedCandidateId(earthSites.find((site) => site.id === "earth-atacama")?.id ?? earthSites[0]?.id ?? null);
      })
      .catch((error) => { if (active) { setBackendError(true); setCatalogError(error instanceof Error ? error.message : "Backend unavailable"); } })
      .finally(() => { if (active) setCatalogLoading(false); });
    Promise.allSettled([api.aoi("earth-atacama"), api.aoi("earth-upper-mustang"), api.aoi("earth-ladakh"), api.aoi("mars-jezero"), api.terrain("mars-jezero"), api.terrain("earth-atacama"), api.sources()]).then((items) => {
      if (!active) return;
      setAois(items.slice(0, 4).flatMap((item) => item.status === "fulfilled" ? [item.value as AoiFeature] : []));
      const summaries = items.slice(4, 6).flatMap((item) => item.status === "fulfilled" ? [item.value as TerrainSummary] : []);
      setTerrain(Object.fromEntries(summaries.map((summary) => [summary.site_id, summary])));
      if (items[6].status === "fulfilled") setSources(items[6].value as SourceManifest[]);
    });
    return () => { active = false; };
  }, []);

  const handleSiteSelect = useCallback((site: Site) => {
    setFocusedCandidateId(site.id);
    setResultsStale(false);
  }, []);
  const handleZoomChange = useCallback((value: boolean) => setIsZoomedIn(value), []);
  const clearComparisonState = useCallback(() => {
    setResults([]);
    setResultsStale(false);
    setComparisonError(null);
    setComparisonAttempted(false);
  }, []);
  const toggleCandidate = (id: string) => {
    setFocusedCandidateId(id);
    clearComparisonState();
    setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  const focusCandidate = useCallback((id: string) => {
    setFocusedCandidateId(id);
    clearComparisonState();
  }, [clearComparisonState]);
  const selectAllReal = useCallback(() => {
    setSelectedIds(sites.filter((site) => site.data_status === "real_processed").map((site) => site.id));
    clearComparisonState();
  }, [sites, clearComparisonState]);

  const compareTerrain = useCallback(async () => {
    if (!selectedIds.length) { setComparisonError("Select at least one real Earth site."); setComparisonAttempted(true); return; }
    setComparisonLoading(true); setComparisonError(null);
    setComparisonAttempted(true);
    try {
      const response = await api.discover(selectedIds);
      setResults(response.results);
      setResultsStale(false);
      window.requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (error) {
      setResultsStale(results.length > 0);
      setComparisonError(error instanceof Error ? error.message : "Comparison request failed");
    } finally { setComparisonLoading(false); }
  }, [selectedIds, results.length]);

  function downloadResult(result: ComparisonResult) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${result.reference_site.id}-${result.candidate_site.id}.json`; anchor.click(); URL.revokeObjectURL(url);
  }

  const referenceTerrain = terrain["mars-jezero"];
  const selectedSite = useMemo(() => sites.find((site) => site.id === focusedCandidateId) ?? null, [sites, focusedCandidateId]);
  useEffect(() => {
    if (!selectedSite || terrain[selectedSite.id]) return;
    const controller = new AbortController();
    api.terrain(selectedSite.id, controller.signal)
      .then((summary) => setTerrain((current) => ({ ...current, [summary.site_id]: summary })))
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setTerrainError({ siteId: selectedSite.id, message: error instanceof Error ? error.message : "Terrain summary unavailable" });
      });
    return () => controller.abort();
  }, [selectedSite, terrain]);
  const filteredSites = useMemo(() => dataFilter === "all" ? sites : sites.filter((site) => site.data_status === dataFilter), [sites, dataFilter]);
  const earthAois = useMemo(() => aois.filter((aoi) => aoi.properties.planetary_body === "earth"), [aois]);
  const candidateCounts = useMemo(() => ({ all: sites.length, real_processed: sites.filter((site) => site.data_status === "real_processed").length, demo_fixture: sites.filter((site) => site.data_status === "demo_fixture").length, metadata_only: sites.filter((site) => site.data_status === "metadata_only").length }), [sites]);
  const selectedAoi = aois.find((aoi) => aoi.properties.site_id === selectedSite?.id);
  const selectedTerrain = selectedSite ? terrain[selectedSite.id] : undefined;
  const selectedSourceId = selectedSite ? ({ "earth-atacama": "earth-atacama-srtmgl1", "earth-upper-mustang": "earth-upper-mustang-srtmgl1", "earth-ladakh": "earth-ladakh-srtmgl1" } as Record<string, string>)[selectedSite.id] : undefined;
  const selectedSource = sources.find((source) => source.source_id === selectedSourceId);
  const jezeroSource = sources.find((source) => source.source_id === "mars-jezero-ctx-dem");
  const selectedRealCount = selectedIds.filter((id) => sites.some((site) => site.id === id && site.data_status === "real_processed")).length;
  const realSitesAvailable = candidateCounts.real_processed > 0;
  const comparisonButtonLabel = comparisonLoading ? "Comparing…" : selectedRealCount ? `Compare ${selectedRealCount} site${selectedRealCount === 1 ? "" : "s"}` : "Select real sites to compare";

  return <main className="space-environment">
    <div className="nebula-background" />
    <header className="space-header"><div><h1>TERRALUNA AI</h1><p>Terrain analog explorer · Earth study areas compared with Mars</p></div><div className={`system-status ${backendError ? "status-error" : ""}`}><span className="status-dot" />{backendError ? "Backend unavailable" : !health ? "Checking data service…" : `${health.data_counts.rankable_real_candidates} real Earth sites available`}</div></header>
    <div className="selector-container"><PlanetSelector activePlanet={activePlanet} onChange={setActivePlanet} /></div>
    <div className="dashboard-grid">
    <section className="planet-stage">
      {activePlanet === "earth" && <><div className="earth-map">{catalogLoading ? <div className="stage-message">Loading backend candidates…</div> : sites.length ? <CandidateMap sites={filteredSites} aois={earthAois} focusedSiteId={focusedCandidateId} onSelect={handleSiteSelect} onZoomChange={handleZoomChange} /> : <div className="stage-message error-state">No backend candidates are available. Start the API and retry.</div>}</div><SpaceScene onMoonClick={() => setActivePlanet("moon")} showOrbit={!isZoomedIn} /></>}
      {activePlanet === "mars" && <><div className="planet-viewer"><PlanetViewer planet="mars" /></div><div className="reference-overlay"><span>PHASE 3 REFERENCE · REAL DEM</span><h2>{reference?.name ?? "Jezero Crater"}</h2><p>{reference?.short_description ?? "Reference metadata unavailable while the backend is offline."}</p><small>{referenceTerrain?.aoi_id ?? "AOI unavailable"} · {referenceTerrain?.analysis_width_m ? `${(referenceTerrain.analysis_width_m / 1000).toFixed(2)} km square` : "size unavailable"} · {referenceTerrain?.resolution_m ?? "—"} m grid</small><p className="source-line">{jezeroSource?.provider} · {jezeroSource?.instrument}<br />Coverage {referenceTerrain ? `${(referenceTerrain.valid_coverage_fraction * 100).toFixed(1)}%` : "—"} · Method {String(referenceTerrain?.calculation_metadata.methodology_version ?? "—")}</p></div></>}
      {activePlanet === "moon" && <div className="coming-soon"><div className="moon-preview"><PlanetViewer planet="moon" /></div><div className="coming-copy"><span>LATER PHASE</span><h2>Moon analysis coming in a later phase.</h2><p>No Moon terrain pipeline or comparison result is claimed in this phase.</p></div></div>}
    </section>

    <section className="workspace-panel" aria-label="Terrain comparison workspace">
      <div className="candidate-column">
        <div className="workflow-heading"><p className="eyebrow">EARTH CANDIDATES</p><h2>Compare Earth terrain to Jezero Crater, Mars</h2><p className="panel-muted">Select real processed study areas to rank them using the same terrain-v2.0 method and 60 m comparison grid.</p></div>
        <article className="reference-card"><div><span className="reference-kicker">REFERENCE SITE</span><h3>Jezero Crater</h3><p>Mars · real processed CTX DEM</p></div><strong>60 m grid</strong></article>
        <div className="filter-toolbar"><div className="data-filters" aria-label="Candidate data filters">{([['real_processed','Real data'],['all','All sites'],['demo_fixture','Demo preview'],['metadata_only','Metadata only']] as const).map(([id,text]) => <button type="button" className={dataFilter === id ? "active" : ""} key={id} onClick={() => { setDataFilter(id); clearComparisonState(); }}>{text} <b>{candidateCounts[id]}</b></button>)}</div>{realSitesAvailable && <button className="select-all-button" type="button" onClick={selectAllReal}>Select all real sites</button>}</div>
        {catalogLoading && <p>Loading candidate catalog…</p>}{catalogError && <p className="error-text" role="alert">Could not load the candidate catalog: {catalogError}</p>}{!catalogLoading && !filteredSites.length && <p className="empty-inline">No sites match this filter.</p>}
        <div className="candidate-list">{filteredSites.map((site) => {
          const eligible = site.data_status === "real_processed";
          const inspected = focusedCandidateId === site.id;
          return <div data-testid={`candidate-${site.id}`} key={site.id} className={`candidate-row ${inspected ? "focused" : ""} ${selectedIds.includes(site.id) ? "selected" : ""} ${!eligible ? "not-eligible" : ""}`}>
            <input aria-label={`Include ${site.name} in comparison`} type="checkbox" disabled={!eligible} checked={selectedIds.includes(site.id)} onChange={() => toggleCandidate(site.id)} />
            <button type="button" className="site-inspect-button" onClick={() => focusCandidate(site.id)}><strong>{site.name}</strong><span>{site.country_or_region} · {inspected ? "Inspecting" : "Inspect site"}</span></button>
            <em className={`data-badge ${site.data_status}`}>{dataLabel(site.data_status)}</em>
            {!eligible && <small>{site.data_status === "demo_fixture" ? "Preview only; cannot enter a real ranking." : "No validated terrain summary."}</small>}
          </div>;
        })}</div>
        <div className="compare-action"><button className="compare-button" type="button" onClick={compareTerrain} disabled={comparisonLoading || backendError || !selectedRealCount}>{comparisonButtonLabel}</button><span>{selectedRealCount ? `${selectedRealCount} real site${selectedRealCount === 1 ? "" : "s"} selected` : "Choose at least one real site to enable comparison."}</span></div>
        {comparisonError && <div className="request-error" role="alert"><strong>Comparison request failed.</strong><p>{comparisonError}. Your site selection is preserved.</p><button type="button" onClick={compareTerrain}>Retry comparison</button></div>}
      </div>
      <div className="evidence-column">
        <div ref={resultsRef} className="results-list" data-testid="results-panel">
          {resultsStale && results.length > 0 && <div className="stale-result" role="status">Previous result shown. The latest comparison request failed.</div>}
          {!results.length && <div className="empty-state">{comparisonAttempted ? "No result was returned. Check the request status above and retry." : "Your ranked terrain results will appear here after you compare the selected sites."}</div>}
          {results.some((result) => result.ranking_scope === "real_only") && <h3 className="result-section-title">Real terrain ranking</h3>}
          {results.filter((result) => result.ranking_scope === "real_only").map((result, index) => <ResultCard result={result} rank={index + 1} onDownload={downloadResult} key={result.candidate_site.id} />)}
          {results.some((result) => result.ranking_scope === "preview_only") && <h3 className="result-section-title">Preview candidates</h3>}
          {results.filter((result) => result.ranking_scope === "preview_only").map((result, index) => <ResultCard result={result} rank={index + 1} onDownload={downloadResult} key={result.candidate_site.id} />)}
        </div>
        {selectedSite ? <article className="site-card" data-testid="selected-candidate-details"><div><p className="eyebrow">INSPECTING SITE</p><h3>{selectedSite.name}</h3></div><em className={`data-badge ${selectedSite.data_status}`}>{dataLabel(selectedSite.data_status)}</em><p>{selectedSite.short_description}</p>{terrainError?.siteId === selectedSite.id && <p className="warning-text" role="alert">Dataset details unavailable: {terrainError.message}</p>}<dl><dt>Study window</dt><dd>{selectedAoi ? `${selectedAoi.properties.width_m / 1000} × ${selectedAoi.properties.height_m / 1000} km · ${selectedAoi.properties.aoi_id}` : "Regional locator only; no verified AOI footprint"}</dd><dt>Source resolution</dt><dd>{selectedSource?.native_resolution ?? "Not available"}{selectedTerrain?.resolution_m ? ` · processed on a ${selectedTerrain.resolution_m} m grid` : ""}</dd><dt>Data quality</dt><dd>{selectedTerrain ? `${(selectedTerrain.valid_coverage_fraction * 100).toFixed(1)}% valid coverage` : selectedSite.data_status === "real_processed" ? "Processed summary loading…" : "No validated terrain summary"}</dd><dt>Known limits</dt><dd>{selectedSite.known_limitations.join(" ")}</dd></dl>{selectedSource && <a className="source-link" href={selectedSource.source_page_url} target="_blank" rel="noreferrer">Open source record ↗</a>}</article> : <div className="empty-state">Select a site name or map marker to inspect its data.</div>}
      </div>
    </section>
    </div>
  </main>;
}

