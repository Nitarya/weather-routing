import {
  Alert,
  Autocomplete,
  Badge,
  Button,
  NumberInput,
  Paper,
  SegmentedControl,
  Skeleton,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { formatMiles } from "../lib/format";
import { RouteCard } from "./RouteCard";
import { Logo } from "./Logo";
import { ArrowRight, Calendar, MapPin, Sparkles, Warning, Weight } from "./Icons";
import locations from "../data/locations.json";

const fieldClassNames = {
  label: "mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400",
  input: "border-white/10 bg-ink-950/50 placeholder:text-slate-600",
};

function locationSuggestions(query) {
  const term = query.trim().toLowerCase();
  if (!term) return [];
  return locations.locations
    .filter((location) => location.toLowerCase().includes(term))
    .slice(0, 8);
}

function Hero() {
  return (
    <div>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <span className="h-1.5 w-1.5 rounded-full bg-brand shadow-[0_0_8px_rgba(64,224,208,0.8)]" />
        Weather-aware routing
      </div>
      <h1 className="mt-3 text-4xl font-semibold leading-[1.02] tracking-[-0.045em] text-white">
        Routes that respect
        <br />
        <span className="text-brand">the weather.</span>
      </h1>
      <p className="mt-2.5 max-w-[330px] text-sm leading-relaxed text-slate-400">
        Compare three truck routes against checkpoint forecasts, load limits and
        arrival times.
      </p>
    </div>
  );
}

export function Sidebar({
  config,
  form,
  plan,
  loading,
  error,
  selectedRouteId,
  onChange,
  onSubmit,
  onSelectRoute,
}) {
  const minDate = new Date();
  const maxDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

  return (
    <aside className="sidebar flex w-full shrink-0 flex-col border-b border-white/10 bg-ink-900/90 lg:h-screen lg:w-[430px] lg:border-b-0 lg:border-r">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/10 px-5">
        <Logo />
        <span className="live-badge inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-xs uppercase tracking-[0.12em] text-brand">
          <i className="h-1.5 w-1.5 rounded-full bg-brand" />
          Live
        </span>
      </header>

      <div className="sidebar-scroll flex-1 space-y-5 overflow-y-auto px-5 py-5">
        <Hero />

        <Paper
          component="form"
          withBorder
          radius="lg"
          p="md"
          className="planner-card border-white/10 bg-white/[0.035]"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <div className="space-y-3.5">
            <Autocomplete
              id="origin"
              label="Origin"
              placeholder="City, state or address"
              leftSection={<MapPin size={16} />}
              data={locationSuggestions(form.originText)}
              value={form.originText}
              onChange={(value) => onChange({ originText: value })}
              limit={6}
              maxDropdownHeight={220}
              comboboxProps={{ withinPortal: true }}
              required
              classNames={fieldClassNames}
            />

            <Autocomplete
              id="destination"
              label="Destination"
              placeholder="City, state or address"
              leftSection={<MapPin size={16} />}
              data={locationSuggestions(form.destinationText)}
              value={form.destinationText}
              onChange={(value) => onChange({ destinationText: value })}
              limit={6}
              maxDropdownHeight={220}
              comboboxProps={{ withinPortal: true }}
              required
              classNames={fieldClassNames}
            />

            <DateTimePicker
              id="departure"
              label="Departure"
              placeholder="Pick date and time"
              leftSection={<Calendar size={15} />}
              value={form.departure || null}
              onChange={(value) => onChange({ departure: value ?? "" })}
              valueFormat="MMM D, YYYY h:mm A"
              minDate={minDate}
              maxDate={maxDate}
              timePickerProps={{ withSeconds: false }}
              dropdownType="modal"
              modalProps={{ centered: true, size: "md" }}
              clearable
              required
              classNames={fieldClassNames}
            />

            <NumberInput
              id="load"
              label="Load weight"
              placeholder="44,000"
              leftSection={<Weight size={15} />}
              value={form.load === "" ? "" : Number(form.load)}
              onChange={(value) => onChange({ load: value === "" ? "" : String(value) })}
              min={0}
              max={200000}
              step={500}
              suffix=" lb"
              thousandSeparator=","
              required
              classNames={fieldClassNames}
            />

            <div className="flex items-center justify-between gap-3 pt-0.5">
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                <MapPin size={12} />
                Sample weather every
              </span>
              <SegmentedControl
                value={`${form.interval} mi`}
                onChange={(value) => onChange({ interval: Number.parseInt(value, 10) })}
                data={config?.sample_intervals?.map((interval) => `${interval} mi`) ?? [
                  "10 mi",
                  "25 mi",
                  "50 mi",
                ]}
                aria-label="Weather sampling interval"
              />
            </div>

            <Button
              type="submit"
              color="pink"
              fullWidth
              size="md"
              loading={loading}
              rightSection={loading ? undefined : <ArrowRight size={16} />}
              className="plan-button mt-0.5"
            >
              {loading ? "Fetching weather…" : "Plan route"}
            </Button>

            <p className="flex items-center gap-1.5 text-xs leading-relaxed text-slate-500">
              <span className="h-1 w-1 rounded-full bg-brand" />
              Weather at every checkpoint uses its estimated arrival time
            </p>
          </div>
        </Paper>

        <section className="results space-y-3" aria-live="polite">
          <div className="flex items-end justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Output
              </span>
              <h2 className="mt-0.5 text-lg font-semibold tracking-tight text-white">
                Route options
              </h2>
            </div>
            {plan && (
              <span className="text-xs text-slate-500">
                {plan.routes.length} routes · {plan.sample_interval_miles} mi sampling
              </span>
            )}
          </div>

          {error && (
            <Alert
              color="red"
              variant="light"
              radius="md"
              title="Route planning failed"
              icon={<Warning size={15} />}
            >
              <p className="text-xs leading-relaxed">{error}</p>
              <Button
                variant="subtle"
                color="red"
                size="sm"
                mt={6}
                px={0}
                onClick={onSubmit}
                rightSection={<ArrowRight size={11} />}
              >
                Try again
              </Button>
            </Alert>
          )}

          {loading && !plan && (
            <div className="space-y-2" aria-label="Loading routes">
              {[0, 1, 2].map((index) => (
                <Paper key={index} withBorder radius="lg" p="md" className="border-white/10">
                  <Skeleton height={8} width="42%" radius="xl" />
                  <Skeleton height={7} width="72%" mt={9} radius="xl" />
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <Skeleton height={30} radius="md" />
                    <Skeleton height={30} radius="md" />
                    <Skeleton height={30} radius="md" />
                  </div>
                </Paper>
              ))}
            </div>
          )}

          {!loading && !plan && !error && (
            <Paper
              withBorder
              radius="lg"
              p="lg"
              className="empty-card flex flex-col items-center border-dashed border-white/10 bg-white/[0.02] text-center"
            >
              <span className="grid h-9 w-9 place-items-center rounded-full bg-brand/10 text-brand">
                <MapPin size={17} />
              </span>
              <strong className="mt-2 text-sm font-semibold text-slate-200">
                Ready when you are
              </strong>
              <p className="mt-0.5 text-xs text-slate-500">
                Enter a lane above to compare weather, risk and ETAs.
              </p>
            </Paper>
          )}

          {plan && (
            <>
              <Paper
                withBorder
                radius="md"
                p="sm"
                className="recommendation flex gap-2.5 border-brand/20 bg-brand/[0.05]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand/10 text-brand">
                  <Sparkles size={14} />
                </span>
                <div className="min-w-0">
                  <Badge color="brand" variant="light" size="sm" tt="uppercase">
                    Recommended
                  </Badge>
                  <p className="mt-1 text-xs leading-relaxed text-slate-300">
                    {plan.recommendation.reason}
                  </p>
                </div>
              </Paper>

              <div className="space-y-2">
                {plan.routes.map((route) => (
                  <RouteCard
                    key={route.id}
                    route={route}
                    selected={route.id === selectedRouteId}
                    onSelect={onSelectRoute}
                  />
                ))}
              </div>

              <p className="text-xs text-slate-500">
                {formatMiles(plan.request.load_lb)} lb load · {plan.routes.length}{" "}
                routes ranked by safety
              </p>

              {plan.warnings.length > 0 && (
                <div className="space-y-1.5">
                  {plan.warnings.map((warning) => (
                    <Alert
                      key={warning}
                      color="yellow"
                      variant="light"
                      radius="sm"
                      icon={<Warning size={13} />}
                    >
                      <span className="text-xs leading-relaxed">{warning}</span>
                    </Alert>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </aside>
  );
}
