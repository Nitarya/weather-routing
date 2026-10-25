import { Badge, Group, Paper, Slider, Text } from "@mantine/core";
import { formatDayClock, relativeHourLabel } from "../lib/format";
import { RISK_COLORS, RISK_LABELS } from "../constants";
import { RiskLegend } from "./Risk";

const MAX_HOUR = 48;
const MARKS = [0, 12, 24, 36, 48].map((value) => ({
  value,
  label: value === 0 ? "Departure" : `+${value}h`,
}));

export function HeatmapControls({ heatmap, loading, hour, onHourChange }) {
  const summary = heatmap?.summary[Math.min(hour, heatmap.summary.length - 1)];
  const highest = summary?.highest_level ?? "low";
  const maxHour = heatmap ? Math.max(0, heatmap.hours.length - 1) : MAX_HOUR;
  const displayHour = Math.min(hour, maxHour);

  return (
    <Paper
      withBorder
      radius="lg"
      p="sm"
      className="heatmap-controls absolute bottom-3 left-3 right-3 z-20 border-white/10 bg-ink-900/90 shadow-2xl backdrop-blur-md xl:right-[352px]"
    >
      <Group justify="space-between" align="flex-start" gap="xs">
        <div>
          <Group gap={6}>
            <Text className="hm-title" size="sm" fw={600} c="white">
              Weather heatmap
            </Text>
            <Badge size="sm" variant="light" color="brand">
              48H
            </Badge>
          </Group>
          <Group className="hm-time" gap={6} mt={2}>
            {loading && !heatmap ? (
              <Text size="sm" c="dimmed" className="hm-loading">
                Building weather heatmap…
              </Text>
            ) : heatmap && summary ? (
              <>
                <Text size="sm" fw={600} c="white">
                  {relativeHourLabel(displayHour)}
                </Text>
                <Text size="sm" c="dimmed">
                  {formatDayClock(heatmap.hours[displayHour])}
                </Text>
                <Badge
                  size="sm"
                  variant="light"
                  radius="xl"
                  styles={{
                    root: {
                      color: RISK_COLORS[highest],
                      backgroundColor: `${RISK_COLORS[highest]}16`,
                      borderColor: `${RISK_COLORS[highest]}33`,
                    },
                  }}
                  leftSection={<i className="h-1 w-1 rounded-full" style={{ background: RISK_COLORS[highest] }} />}
                >
                  {highest === "low" ? "Low risk" : `${RISK_LABELS[highest]} conditions`}
                </Badge>
              </>
            ) : (
              <Text size="sm" c="dimmed" className="hm-loading">
                No heatmap available
              </Text>
            )}
          </Group>
        </div>
      </Group>

      <div className="hm-slider mt-3">
        <Slider
          min={0}
          max={maxHour}
          step={1}
          value={displayHour}
          onChange={onHourChange}
          disabled={!heatmap}
          label={(value) => relativeHourLabel(value)}
          marks={MARKS}
          size="sm"
          color="brand"
          aria-label="Forecast hour"
          classNames={{ markLabel: "text-xs text-slate-500" }}
        />
      </div>

      <div className="hm-footer mt-4 flex flex-wrap items-center justify-between gap-2">
        <RiskLegend />
        <Text size="xs" c="dimmed">
          {heatmap && summary && highest === "low"
            ? "No moderate+ cells this hour"
            : "Moderate+ cells shaded"}
        </Text>
      </div>
    </Paper>
  );
}
