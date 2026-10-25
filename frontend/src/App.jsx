import { useCallback, useEffect, useRef, useState } from "react";
import dayjs from "dayjs";
import { CheckpointPanel } from "./components/CheckpointPanel";
import { HeatmapControls } from "./components/HeatmapControls";
import { MapView } from "./components/MapView";
import { Sidebar } from "./components/Sidebar";
import { TripSummary } from "./components/TripSummary";
import { WeatherLoader } from "./components/WeatherLoader";
import { MapPin } from "./components/Icons";
import { fetchConfig, fetchHeatmap, planTrip } from "./lib/api";
import { parseDateTime, toIso } from "./lib/format";

function initialForm() {
  return {
    originText: "Green River, WY",
    destinationText: "Minneapolis, MN",
    departure: dayjs().add(24, "hour").startOf("minute").format("YYYY-MM-DD HH:mm:ss"),
    load: "25000",
    interval: 50,
  };
}

function buildRequest(form) {
  return {
    origin: form.originText.trim(),
    destination: form.destinationText.trim(),
    departure_time: toIso(form.departure),
    load_lb: Number(form.load),
    sample_interval_miles: form.interval,
  };
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [plan, setPlan] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [hour, setHour] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [heatmapError, setHeatmapError] = useState(null);
  const [focus, setFocus] = useState(null);
  const [popupOpen, setPopupOpen] = useState(false);
  const planSeq = useRef(0);
  const heatSeq = useRef(0);

  useEffect(() => {
    let cancelled = false;
    fetchConfig()
      .then((value) => {
        if (!cancelled) setConfig(value);
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load the app configuration.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadHeatmap = useCallback(async (activePlan, route) => {
    const seq = ++heatSeq.current;
    setHeatmap(null);
    setHeatmapLoading(true);
    setHeatmapError(null);
    try {
      const data = await fetchHeatmap({
        polyline: route.polyline,
        departure_time: activePlan.departure_time,
        load_lb: activePlan.load_lb,
        hours: 48,
      });
      if (seq === heatSeq.current) setHeatmap(data);
    } catch (reason) {
      if (seq === heatSeq.current) {
        setHeatmapError(
          reason instanceof Error ? reason.message : "Could not build the heatmap.",
        );
      }
    } finally {
      if (seq === heatSeq.current) setHeatmapLoading(false);
    }
  }, []);

  const submit = async () => {
    if (!form.originText.trim() || !form.destinationText.trim()) {
      setError("Enter an origin and destination.");
      return;
    }
    if (!form.departure) {
      setError("Choose a departure date and time.");
      return;
    }
    if (!form.load.trim()) {
      setError("Enter the load weight.");
      return;
    }
    if (!Number.isFinite(Number(form.load))) {
      setError("Load weight must be a number.");
      return;
    }

    const departure = parseDateTime(form.departure);
    if (!departure) {
      setError("Choose a valid departure date and time.");
      return;
    }
    if (departure.getTime() < Date.now() - 60_000) {
      setError("Departure cannot be in the past.");
      return;
    }
    if (departure.getTime() > Date.now() + 7 * 24 * 60 * 60 * 1000) {
      setError("Departure must be within the next 7 days.");
      return;
    }

    const seq = ++planSeq.current;
    setLoading(true);
    setError(null);
    setPlan(null);
    setSelectedRouteId(null);
    setHeatmap(null);
    setHeatmapError(null);
    setHour(0);

    try {
      const nextPlan = await planTrip(buildRequest(form));
      if (seq !== planSeq.current) return;
      setPlan(nextPlan);
      const recommended =
        nextPlan.routes.find((route) => route.is_recommended) ?? nextPlan.routes[0];
      setSelectedRouteId(recommended?.id ?? null);
      if (recommended) void loadHeatmap(nextPlan, recommended);
    } catch (reason) {
      if (seq === planSeq.current) {
        setError(reason instanceof Error ? reason.message : "Could not plan this route.");
      }
    } finally {
      if (seq === planSeq.current) setLoading(false);
    }
  };

  const handleSelectRoute = (routeId) => {
    if (!plan || routeId === selectedRouteId) return;
    const route = plan.routes.find((item) => item.id === routeId);
    if (!route) return;
    setSelectedRouteId(routeId);
    setFocus(null);
    setHour(0);
    void loadHeatmap(plan, route);
  };

  const handleFocusCheckpoint = (index) => {
    const route = plan?.routes.find((item) => item.id === selectedRouteId);
    const checkpoint = route?.checkpoints[index];
    if (!checkpoint) return;
    setFocus({ lat: checkpoint.lat, lng: checkpoint.lng, index, nonce: Date.now() });
  };

  const selectedRoute =
    plan?.routes.find((route) => route.id === selectedRouteId) ??
    plan?.routes.find((route) => route.is_recommended) ??
    plan?.routes[0] ??
    null;

  return (
    <div className="min-h-screen bg-ink-950 text-slate-100 lg:flex lg:h-screen lg:overflow-hidden">
      <Sidebar
        config={config}
        form={form}
        plan={plan}
        loading={loading}
        error={error}
        selectedRouteId={selectedRouteId}
        onChange={(patch) => setForm((current) => ({ ...current, ...patch }))}
        onSubmit={submit}
        onSelectRoute={handleSelectRoute}
      />

      <main className="map-shell relative h-[62vh] min-h-[520px] w-full bg-ink-950 lg:h-full lg:min-h-0 lg:flex-1">
        <MapView
          apiKey={config?.map_api_key ?? null}
          plan={plan}
          selectedRouteId={selectedRouteId}
          heatmap={heatmap}
          hour={hour}
          focus={focus}
          onSelectRoute={handleSelectRoute}
          onPopupChange={setPopupOpen}
        />

        {plan && selectedRoute ? (
          <>
            {!popupOpen && <TripSummary plan={plan} route={selectedRoute} />}
            <CheckpointPanel
              plan={plan}
              route={selectedRoute}
              onFocus={handleFocusCheckpoint}
            />
            <HeatmapControls
              heatmap={heatmap}
              loading={heatmapLoading}
              hour={hour}
              onHourChange={setHour}
            />
          </>
        ) : (
          <div className="map-empty absolute inset-0 z-10 grid place-items-center bg-ink-950/20 p-6">
            <div className="map-empty-card w-full max-w-md rounded-2xl border border-white/10 bg-ink-900/90 p-6 shadow-2xl backdrop-blur-md">
              <span className="map-empty-icon mb-3 grid h-10 w-10 place-items-center rounded-xl border border-brand/20 bg-brand/10 text-brand">
                <MapPin size={20} />
              </span>
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Route Weather
              </span>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">
                Weather-aware truck routing.
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                Enter an origin, destination, departure and load. We compare three
                routes, sample the forecast along each one and recommend the safest.
              </p>
            </div>
          </div>
        )}

        {heatmapError && plan && (
          <div
            className="map-toast absolute left-1/2 top-4 z-30 -translate-x-1/2 rounded-full border border-pink/30 bg-ink-900/90 px-3 py-1.5 text-xs text-pink shadow-xl backdrop-blur"
            role="status"
          >
            {heatmapError}
          </div>
        )}

        <WeatherLoader
          active={loading || heatmapLoading}
          mode={loading ? "plan" : "heatmap"}
          interval={form.interval}
        />
      </main>
    </div>
  );
}
