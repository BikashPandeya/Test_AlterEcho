"use client";

import { memo, useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, NavigationControl, Popup, setWorkerUrl } from "maplibre-gl";
import type { Map as MapLibreMapType } from "maplibre-gl";
import type { AoiFeature, Site } from "../../lib/api";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString());

const satelliteStyle = {
  version: 8 as const,
  sources: { satellite: { type: "raster" as const, tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, attribution: "Tiles © Esri" } },
  layers: [{ id: "satellite-layer", type: "raster" as const, source: "satellite", minzoom: 0, maxzoom: 19 }],
};

function CandidateMap({ sites, aois = [], focusedSiteId, onSelect, onZoomChange }: { sites: Site[]; aois?: AoiFeature[]; focusedSiteId: string | null; onSelect: (site: Site) => void; onZoomChange?: (zoomedIn: boolean) => void; }) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMapType | null>(null);
  const sitesRef = useRef(sites);
  const aoisRef = useRef(aois);
  const onSelectRef = useRef(onSelect);
  const onZoomChangeRef = useRef(onZoomChange);
  const [mapError, setMapError] = useState(false);

  useEffect(() => {
    sitesRef.current = sites;
    aoisRef.current = aois;
    onSelectRef.current = onSelect;
    onZoomChangeRef.current = onZoomChange;
  }, [sites, aois, onSelect, onZoomChange]);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = new MapLibreMap({ container: mapContainer.current, style: satelliteStyle, center: [20, 15], zoom: 1.5, minZoom: 1, maxZoom: 12, dragPan: true, dragRotate: true, touchZoomRotate: true, canvasContextAttributes: { antialias: true } });
    mapRef.current = map;
    map.addControl(new NavigationControl(), "top-right");
    map.on("zoom", () => onZoomChangeRef.current?.(map.getZoom() > 1.5005));
    map.on("load", () => {
      map.setProjection({ type: "globe" });
      if (aoisRef.current.length) {
        map.addSource("candidate-aois", { type: "geojson", data: { type: "FeatureCollection", features: aoisRef.current } });
        map.addLayer({ id: "candidate-aoi-fill", type: "fill", source: "candidate-aois", paint: { "fill-color": "#38bdf8", "fill-opacity": 0.18 } });
        map.addLayer({ id: "candidate-aoi-line", type: "line", source: "candidate-aois", paint: { "line-color": "#7dd9ff", "line-width": 2 } });
      }
      map.addSource("candidates", { type: "geojson", data: { type: "FeatureCollection", features: sitesRef.current.map((site) => ({ type: "Feature", geometry: { type: "Point", coordinates: [site.longitude, site.latitude] }, properties: { id: site.id, name: site.name, status: site.data_status } })) } });
      map.addLayer({ id: "candidate-points", type: "circle", source: "candidates", paint: { "circle-radius": 9, "circle-color": ["match", ["get", "status"], "metadata_only", "#94a3b8", "#f97316"], "circle-stroke-width": 2, "circle-stroke-color": "#ffffff" } });
      map.addLayer({ id: "candidate-labels", type: "symbol", source: "candidates", layout: { "text-field": ["get", "name"], "text-offset": [0, 1.5], "text-size": 12, "text-allow-overlap": false }, paint: { "text-color": "#ffffff", "text-halo-color": "#111827", "text-halo-width": 2 } });
      map.on("click", "candidate-points", (event) => {
        const site = sitesRef.current.find((item) => item.id === event.features?.[0]?.properties?.id);
        if (!site) return;
        map.flyTo({ center: [site.longitude, site.latitude], zoom: 6.5, speed: 1.2, curve: 1.4, essential: true });
        onSelectRef.current(site);
        const popup = document.createElement("div"); popup.className = "map-popup";
        const title = document.createElement("strong"); title.textContent = site.name;
        const region = document.createElement("p"); region.textContent = site.country_or_region;
        const status = document.createElement("small"); status.textContent = site.data_status.replace("_", " ");
        popup.append(title, region, status);
        new Popup().setLngLat([site.longitude, site.latitude]).setDOMContent(popup).addTo(map);
      });
      map.on("mouseenter", "candidate-points", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "candidate-points", () => { map.getCanvas().style.cursor = ""; });
    });
    map.on("error", (event) => { console.warn("MapLibre tile warning:", event.error); setMapError(true); });
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const candidates = map.getSource("candidates") as { setData: (data: GeoJSON.FeatureCollection) => void } | undefined;
    candidates?.setData({ type: "FeatureCollection", features: sites.map((site) => ({ type: "Feature", geometry: { type: "Point", coordinates: [site.longitude, site.latitude] }, properties: { id: site.id, name: site.name, status: site.data_status } })) });
    const candidateAois = map.getSource("candidate-aois") as { setData: (data: GeoJSON.FeatureCollection) => void } | undefined;
    candidateAois?.setData({ type: "FeatureCollection", features: aois });
  }, [sites, aois]);

  useEffect(() => {
    const site = sites.find((item) => item.id === focusedSiteId);
    if (site && mapRef.current) mapRef.current.flyTo({ center: [site.longitude, site.latitude], zoom: Math.max(mapRef.current.getZoom(), 4.5), duration: 650, essential: true });
  }, [focusedSiteId, sites]);

  return <><div ref={mapContainer} className="candidate-map" />{mapError && <div className="map-fallback">Map tiles are unavailable. Candidate selection remains available below.</div>}</>;
}

export default memo(CandidateMap);

