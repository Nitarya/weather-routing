import { useEffect, useRef, useState } from "react";
import { decodePolyline } from "../lib/geo";
import { DARK_MAP_STYLES, loadGoogleMaps } from "../lib/googleMaps";
import { HeatmapOverlay } from "../lib/heatmapOverlay";
import { formatDayClock, formatMiles } from "../lib/format";
import { RISK_COLORS } from "../constants";
import { Warning } from "./Icons";
import { fetchReverseGeocode } from "../lib/api";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(checkpoint, route, area = "", areaLoading = false) {
  const risk = checkpoint.risk;
  const areaText = areaLoading
    ? "Locating…"
    : area || "Area unavailable";
  const weather = checkpoint.weather;
  const color = RISK_COLORS[risk.level];
  const reasons = risk.reasons.map((reason) => escapeHtml(reason)).join("<br/>");
  return `
    <div class="w-[300px] p-3 text-slate-200">
      <div class="flex items-center justify-between gap-2">
        <span class="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wider" style="color:${color}">
          <i class="h-1.5 w-1.5 rounded-full" style="background:${color}"></i>${escapeHtml(risk.label)} risk
        </span>
        <span class="text-xs text-slate-500">Mile ${formatMiles(checkpoint.mile)} · ${escapeHtml(route.name)}</span>
      </div>
      <div class="mt-1 truncate text-xs text-slate-400">${escapeHtml(route.description)}</div>
      <div class="mt-1 flex items-center gap-1.5 text-xs">
        <span class="text-slate-500">Area</span>
        <span class="truncate font-medium text-slate-200">${escapeHtml(areaText)}</span>
      </div>
      <div class="mt-1 text-sm font-semibold text-white">${formatDayClock(checkpoint.eta)}</div>
      <div class="mt-2 grid grid-cols-3 gap-1.5">
        <div class="rounded-lg bg-white/5 p-1.5">
          <span class="block text-xs uppercase tracking-wider text-slate-500">Wind</span>
          <strong class="text-xs font-semibold text-slate-100">${weather.wind_mph.toFixed(1)} mph</strong>
        </div>
        <div class="rounded-lg bg-white/5 p-1.5">
          <span class="block text-xs uppercase tracking-wider text-slate-500">Rain</span>
          <strong class="text-xs font-semibold text-slate-100">${weather.rain_in_hr.toFixed(2)} in/hr</strong>
        </div>
        <div class="rounded-lg bg-white/5 p-1.5">
          <span class="block text-xs uppercase tracking-wider text-slate-500">Snow</span>
          <strong class="text-xs font-semibold text-slate-100">${weather.snow_in_hr.toFixed(2)} in/hr</strong>
        </div>
      </div>
      <div class="mt-2 text-xs text-slate-400">
        ${escapeHtml(weather.condition)} · ${weather.temp_f.toFixed(0)}°F · ${weather.visibility_mi.toFixed(1)} mi visibility
      </div>
      <div class="mt-1 text-xs leading-relaxed text-slate-500">${reasons}</div>
    </div>
  `;
}

export function MapView({
  apiKey,
  plan,
  selectedRouteId,
  heatmap,
  hour,
  focus,
  onSelectRoute,
  onPopupChange,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const heatRef = useRef(null);
  const infoRef = useRef(null);
  const linesRef = useRef(new Map());
  const markersRef = useRef([]);
  const checkpointMarkersRef = useRef(new Map());
  const openPopupRef = useRef(null);
  const popupSeqRef = useRef(0);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const selectedRoute =
    plan?.routes.find((route) => route.id === selectedRouteId) ??
    plan?.routes.find((route) => route.is_recommended) ??
    plan?.routes[0] ??
    null;

  useEffect(() => {
    let cancelled = false;
    if (!apiKey || !containerRef.current) {
      if (!apiKey) {
        setStatus("error");
        setError("Add a Google Maps API key to render the map.");
      }
      return;
    }
    setStatus("loading");
    loadGoogleMaps(apiKey)
      .then((googleMaps) => {
        if (cancelled || !containerRef.current) return;
        const map = new googleMaps.maps.Map(containerRef.current, {
          center: { lat: 39.2, lng: -96.5 },
          zoom: 5,
          styles: DARK_MAP_STYLES,
          disableDefaultUI: true,
          zoomControl: true,
          zoomControlOptions: { position: googleMaps.maps.ControlPosition.RIGHT_BOTTOM },
          fullscreenControl: false,
          streetViewControl: false,
          mapTypeControl: false,
          clickableIcons: false,
          gestureHandling: "greedy",
          backgroundColor: "#071c24",
        });
        mapRef.current = map;
        const info = new googleMaps.maps.InfoWindow({
          maxWidth: 340,
          pixelOffset: new googleMaps.maps.Size(0, -8),
        });
        info.addListener("closeclick", () => {
          popupSeqRef.current += 1;
          onPopupChange?.(false);
        });
        map.addListener("click", () => {
          popupSeqRef.current += 1;
          info.close();
          onPopupChange?.(false);
        });
        infoRef.current = info;
        heatRef.current = new HeatmapOverlay(map);
        setStatus("ready");
      })
      .catch((reason) => {
        if (cancelled) return;
        setStatus("error");
        setError(reason.message || "The map could not be loaded.");
      });
    return () => {
      cancelled = true;
      heatRef.current?.destroy();
      heatRef.current = null;
      infoRef.current?.close();
      infoRef.current = null;
      linesRef.current.clear();
      markersRef.current = [];
      checkpointMarkersRef.current.clear();
      mapRef.current = null;
    };
  }, [apiKey]);

  useEffect(() => {
    const map = mapRef.current;
    if (status !== "ready" || !plan || !map || !window.google?.maps) return;
    const googleMaps = window.google.maps;
    linesRef.current.forEach(({ casing, line }) => {
      casing.setMap(null);
      line.setMap(null);
    });
    linesRef.current.clear();
    const bounds = new googleMaps.LatLngBounds();
    for (const route of plan.routes) {
      const path = decodePolyline(route.polyline);
      path.forEach((point) => bounds.extend(point));
      const casing = new googleMaps.Polyline({
        path,
        map,
        strokeColor: "#05212a",
        strokeOpacity: 0.95,
        strokeWeight: 12.5,
        zIndex: 10,
        clickable: true,
      });
      const line = new googleMaps.Polyline({
        path,
        map,
        strokeColor: "#3f6d76",
        strokeOpacity: 0.8,
        strokeWeight: 3,
        zIndex: 11,
        clickable: true,
      });
      const select = () => onSelectRoute(route.id);
      casing.addListener("click", select);
      line.addListener("click", select);
      linesRef.current.set(route.id, { casing, line });
    }
    const mapWidth = containerRef.current?.clientWidth ?? 1000;
    const compact = window.innerWidth <= 1150 || mapWidth < 600;
    map.fitBounds(
      bounds,
      compact
        ? { top: 76, right: 18, bottom: 166, left: 18 }
        : { top: 90, right: 360, bottom: 190, left: 80 },
    );
    const listener = googleMaps.event.addListenerOnce(map, "idle", () => {
      if (map.getZoom() && map.getZoom() > 8) map.setZoom(8);
    });
    return () => {
      googleMaps.event.removeListener(listener);
    };
  }, [plan, status]);

  useEffect(() => {
    if (!selectedRouteId) return;
    linesRef.current.forEach(({ casing, line }, id) => {
      const selected = id === selectedRouteId;
      casing.setOptions({
        strokeOpacity: selected ? 1 : 0.7,
        strokeWeight: selected ? 12.5 : 8,
        zIndex: selected ? 20 : 10,
      });
      line.setOptions({
        strokeColor: selected ? "#d8fffb" : "#89b3b9",
        strokeOpacity: selected ? 1 : 0.62,
        strokeWeight: selected ? 7.5 : 3.4,
        zIndex: selected ? 21 : 11,
      });
    });
  }, [selectedRouteId, plan, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (status !== "ready" || !selectedRoute || !map || !window.google?.maps) return;
    const googleMaps = window.google.maps;
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];
    checkpointMarkersRef.current.clear();
    infoRef.current?.close();

    const openPopup = (checkpoint) => {
      const info = infoRef.current;
      if (!info) return;
      const seq = ++popupSeqRef.current;
      info.setContent(popupHtml(checkpoint, selectedRoute, "", true));
      info.open({ map, anchor: checkpointMarkersRef.current.get(checkpoint.index) });
      onPopupChange?.(true);
      fetchReverseGeocode(checkpoint.lat, checkpoint.lng)
        .then((area) => {
          if (seq !== popupSeqRef.current || infoRef.current !== info) return;
          info.setContent(popupHtml(checkpoint, selectedRoute, area, false));
        })
        .catch(() => {
          if (seq !== popupSeqRef.current || infoRef.current !== info) return;
          info.setContent(popupHtml(checkpoint, selectedRoute, "", false));
        });
    };
    openPopupRef.current = openPopup;

    selectedRoute.checkpoints.forEach((checkpoint) => {
      const isOrigin = checkpoint.index === 0;
      const isDestination = checkpoint.index === selectedRoute.checkpoints.length - 1;
      const color = RISK_COLORS[checkpoint.risk.level];
      const marker = new googleMaps.Marker({
        map,
        position: { lat: checkpoint.lat, lng: checkpoint.lng },
        zIndex: isOrigin || isDestination ? 60 : 40,
        title: isOrigin
          ? `Origin · ${plan?.origin.label ?? ""}`
          : isDestination
            ? `Destination · ${plan?.destination.label ?? ""}`
            : `Mile ${formatMiles(checkpoint.mile)} · ${checkpoint.risk.label} risk`,
        icon: {
          path: googleMaps.SymbolPath.CIRCLE,
          scale: isOrigin || isDestination ? 10 : 3.4,
          fillColor: isOrigin ? "#f64673" : isDestination ? "#40e0d0" : color,
          fillOpacity: 1,
          strokeColor: "#04151c",
          strokeWeight: isOrigin || isDestination ? 3 : 1.5,
        },
        label:
          isOrigin || isDestination
            ? {
                text: isOrigin ? "A" : "B",
                color: "#04151c",
                fontSize: "11px",
                fontWeight: "800",
              }
            : undefined,
      });
      marker.addListener("click", () => openPopup(checkpoint));
      markersRef.current.push(marker);
      checkpointMarkersRef.current.set(checkpoint.index, marker);
    });
    return () => {
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      checkpointMarkersRef.current.clear();
    };
  }, [selectedRoute, status, plan]);

  useEffect(() => {
    const map = mapRef.current;
    if (!focus || !map || status !== "ready" || !selectedRoute) return;
    map.panTo({ lat: focus.lat, lng: focus.lng });
    if ((map.getZoom() ?? 0) < 6) map.setZoom(6);
    const checkpoint = selectedRoute.checkpoints[focus.index];
    if (checkpoint) openPopupRef.current?.(checkpoint, selectedRoute);
  }, [focus, selectedRoute, status]);

  useEffect(() => {
    if (status !== "ready" || !heatRef.current) return;
    if (heatmap) {
      heatRef.current.setData(heatmap.cells, heatmap.spacing_miles);
      heatRef.current.setHour(hour);
    } else {
      heatRef.current.clear();
    }
  }, [heatmap, status]);

  useEffect(() => {
    if (status !== "ready") return;
    heatRef.current?.setHour(hour);
  }, [hour, status]);

  return (
    <div className="map-stage relative h-full w-full">
      <div ref={containerRef} className="map-canvas absolute inset-0" />
      {status === "loading" && (
        <div
          className="map-placeholder absolute inset-0 z-10 grid place-items-center gap-2 bg-ink-950/60 text-xs text-slate-400"
          aria-live="polite"
        >
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand/20 border-t-brand" />
          <span>Loading map</span>
        </div>
      )}
      {status === "error" && (
        <div className="map-placeholder map-error absolute inset-0 z-10 grid place-items-center bg-ink-950/90 p-6">
          <div className="max-w-sm rounded-2xl border border-pink/25 bg-ink-900 p-5 text-center">
            <span className="map-error-icon mx-auto mb-2 grid h-10 w-10 place-items-center rounded-full bg-pink/10 text-pink">
              <Warning size={20} />
            </span>
            <strong className="block text-sm font-semibold text-white">
              Map unavailable
            </strong>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">{error}</p>
            <p className="mt-1 text-xs text-slate-500">
              Route data, checkpoints and risk levels are still available in the sidebar.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
