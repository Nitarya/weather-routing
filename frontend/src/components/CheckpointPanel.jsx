import { useState } from "react";
import { formatClock, formatDay, formatMiles } from "../lib/format";
import { RISK_COLORS, RISK_LABELS } from "../constants";
import { ChevronDown, Rain, Snow, Thermometer, Wind } from "./Icons";

export function CheckpointPanel({ plan, route, onFocus }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <section
      className="checkpoint-panel absolute right-3 top-3 z-20 hidden w-[320px] max-h-[calc(100%-250px)] flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink-900/95 shadow-2xl backdrop-blur-md xl:flex"
    >
      <header className="flex items-start justify-between gap-2 border-b border-white/10 px-4 py-3">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Checkpoints
          </span>
          <h3 className="mt-0.5 text-sm font-semibold text-white">
            {route.checkpoints.length} forecast points
          </h3>
          <p className="mt-0.5 truncate text-xs text-slate-500">
            {route.name} · via {route.description}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            every {plan.sample_interval_miles} mi · local times
          </p>
        </div>
        <button
          type="button"
          className="icon-button grid h-6 w-6 place-items-center rounded-md text-slate-400 transition hover:bg-white/10 hover:text-white"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand checkpoints" : "Collapse checkpoints"}
          aria-expanded={!collapsed}
        >
          <ChevronDown
            size={14}
            className={collapsed ? "rotate-180 transition" : "transition"}
          />
        </button>
      </header>

      {!collapsed && (
        <>
          <div className="checkpoint-list flex-1 space-y-0 overflow-y-auto px-2.5 py-2">
            {route.checkpoints.map((checkpoint, index) => {
              const isFirst = index === 0;
              const isLast = index === route.checkpoints.length - 1;
              const level = checkpoint.risk.level;
              return (
                <button
                  key={checkpoint.index}
                  type="button"
                  className="checkpoint-row group relative flex w-full items-start gap-2.5 rounded-lg px-1.5 py-1.5 text-left transition hover:bg-white/[0.04]"
                  onClick={() => onFocus(index)}
                  title={checkpoint.risk.reasons.join(" · ")}
                >
                  <span className="relative flex w-3 shrink-0 flex-col items-center self-stretch">
                    <i
                      className="mt-1 h-2 w-2 shrink-0 rounded-full"
                      style={{
                        background: RISK_COLORS[level],
                        boxShadow: `0 0 0 3px ${RISK_COLORS[level]}22, 0 0 10px ${RISK_COLORS[level]}55`,
                      }}
                    />
                    {!isLast && <span className="mt-1 w-px flex-1 bg-white/10" />}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-1.5">
                      {(isFirst || isLast) && (
                        <em className="rounded bg-white/5 px-1 py-0.5 text-xs font-semibold uppercase not-italic tracking-wider text-slate-400">
                          {isFirst ? "Start" : "Arrive"}
                        </em>
                      )}
                      <span className="text-sm font-semibold text-slate-200">
                        {formatClock(checkpoint.eta)}
                      </span>
                      <span className="ml-auto text-xs text-slate-500">
                        {formatMiles(checkpoint.mile)} mi
                      </span>
                    </span>
                    <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-0.5">
                        <Wind size={9} />
                        {checkpoint.weather.wind_mph.toFixed(0)} mph
                      </span>
                      <span className="inline-flex items-center gap-0.5">
                        <Rain size={9} />
                        {checkpoint.weather.rain_in_hr.toFixed(2)}
                      </span>
                      <span className="inline-flex items-center gap-0.5">
                        <Snow size={9} />
                        {checkpoint.weather.snow_in_hr.toFixed(2)}
                      </span>
                      <span className="inline-flex items-center gap-0.5">
                        <Thermometer size={9} />
                        {checkpoint.weather.temp_f.toFixed(0)}°
                      </span>
                    </span>
                  </span>

                  <span
                    className="mt-0.5 shrink-0 rounded-full border px-1.5 py-0.5 text-xs font-medium"
                    style={{
                      color: RISK_COLORS[level],
                      background: `${RISK_COLORS[level]}14`,
                      borderColor: `${RISK_COLORS[level]}33`,
                    }}
                  >
                    {RISK_LABELS[level]}
                  </span>
                </button>
              );
            })}
          </div>
          <footer className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-xs text-slate-500">
            <span>{formatDay(route.eta)} arrival</span>
            <span>{route.checkpoints.length} samples</span>
          </footer>
        </>
      )}
    </section>
  );
}
