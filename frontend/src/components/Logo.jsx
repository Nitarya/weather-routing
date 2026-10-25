export function Logo({ compact = false }) {
  return (
    <div className="flex items-center gap-2" aria-label="Route Weather">
      <span className="text-lg font-semibold tracking-tight text-white">
        Route<span className="text-brand">Weather</span>
      </span>
    </div>
  );
}
