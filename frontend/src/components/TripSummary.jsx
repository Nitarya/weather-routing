import {
  formatClockWithZone,
  formatDuration,
  formatMiles,
  formatWeight,
} from "../lib/format";
import { RISK_COLORS } from "../constants";
import {
  ArrowRight,
  Clock,
  MapPin,
  RouteIcon,
  Sparkles,
  Warning,
  Weight,
} from "./Icons";

export function TripSummary({ plan, route }) {
  const noTravel = route.risk.no_travel_miles > 0;

  return (
    <section
      className="trip-summary absolute left-3 top-3 z-20 hidden w-[410px] overflow-hidden rounded-2xl border border-white/10 bg-ink-900/90 shadow-2xl backdrop-blur-md md:block"
      aria-label="Selected route summary"
    >
      <div className="flex items-center gap-1.5 border-b border-white/10 px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
        <span className="h-1.5 w-1.5 rounded-full bg-brand" />
        {route.is_recommended ? "Recommended route" : "Selected route"}
        <span className="ml-auto rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-xs tracking-normal text-slate-300">
          {route.name}
        </span>
      </div>

      <div className="flex items-center gap-2 px-4 pt-3 text-sm font-semibold text-white">
        <span className="grid h-5 w-5 place-items-center rounded-full bg-pink/15 text-xs font-bold text-pink">
          A
        </span>
        <span>{plan.origin.city || plan.origin.primary}</span>
        <em className="text-xs font-normal not-italic text-slate-500">
          {plan.origin.state}
        </em>
        <ArrowRight size={13} className="mx-1 text-slate-500" />
        <span className="grid h-5 w-5 place-items-center rounded-full bg-brand/15 text-xs font-bold text-brand">
          B
        </span>
        <span>{plan.destination.city || plan.destination.primary}</span>
        <em className="text-xs font-normal not-italic text-slate-500">
          {plan.destination.state}
        </em>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 border-t border-white/10 px-4 py-3">
        {[
          [<RouteIcon size={13} />, formatMiles(route.distance_miles), "mi"],
          [<Clock size={13} />, formatDuration(route.duration_minutes), "drive"],
          [<MapPin size={13} />, formatClockWithZone(route.eta), "arrive"],
          [<Weight size={13} />, formatWeight(plan.load_lb), "lb"],
        ].map(([icon, value, label]) => (
          <div key={label} className="min-w-0">
            <div className="flex items-center gap-1 text-slate-500">{icon}</div>
            <strong className="mt-1 block text-sm font-semibold text-slate-100">
              {value}
            </strong>
            <span className="block text-xs uppercase tracking-wider text-slate-500">
              {label}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-white/10 px-4 py-2">
        <span className="truncate text-xs text-slate-500">{route.description}</span>
        {noTravel ? (
          <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-pink">
            <Warning size={11} />
            No Travel segment
          </span>
        ) : route.is_recommended ? (
          <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-brand">
            <Sparkles size={11} />
            Best balance
          </span>
        ) : (
          <span
            className="shrink-0 text-xs font-medium"
            style={{ color: RISK_COLORS[route.risk.level] }}
          >
            {route.risk.label} risk
          </span>
        )}
      </div>
    </section>
  );
}
