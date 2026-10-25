import { RISK_COLORS, RISK_LABELS, RISK_LEVELS } from "../constants";

export function RiskDot({ level, size = 8 }) {
  return (
    <span
      className="risk-dot inline-block shrink-0 rounded-full"
      style={{
        width: size,
        height: size,
        background: RISK_COLORS[level],
        boxShadow: `0 0 10px ${RISK_COLORS[level]}55`,
      }}
      aria-hidden="true"
    />
  );
}

export function RiskLegend() {
  return (
    <div className="risk-legend flex flex-wrap items-center gap-x-2.5 gap-y-1.5" aria-label="Risk level legend">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        Risk
      </span>
      {RISK_LEVELS.map((level) => (
        <span
          className="inline-flex items-center gap-1 text-xs text-slate-400"
          key={level}
        >
          <RiskDot level={level} size={6} />
          {RISK_LABELS[level]}
        </span>
      ))}
    </div>
  );
}
