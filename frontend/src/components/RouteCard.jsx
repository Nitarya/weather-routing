import { Badge, Group, Paper, Progress, Text } from "@mantine/core";
import { formatClockWithZone, formatDuration, formatMiles } from "../lib/format";
import { RISK_COLORS, RISK_LEVELS, RISK_LABELS } from "../constants";
import { Check, Clock, Sparkles } from "./Icons";

function overallLevel(route) {
  const risk = route.risk;
  if (risk.no_travel_miles > 0) return "no_travel";
  if (risk.severe_miles > 0) return "severe";
  if (risk.high_miles > 0) return "high";
  if (risk.moderate_miles > 0) return "moderate";
  return "low";
}

function riskLabel(level) {
  if (level === "low") return "All clear";
  if (level === "no_travel") return "No travel";
  if (level === "high") return "High risk";
  return RISK_LABELS[level];
}

export function RouteCard({ route, selected, onSelect }) {
  const level = overallLevel(route);
  const totalMiles = Math.max(1, route.distance_miles);
  const segments = RISK_LEVELS.filter((key) => (route.risk.miles[key] ?? 0) > 0);

  return (
    <Paper
      component="button"
      type="button"
      withBorder
      radius="lg"
      p="sm"
      onClick={() => onSelect(route.id)}
      aria-pressed={selected}
      className={`route-card block w-full text-left transition ${
        selected
          ? "is-selected border-brand/60 bg-brand/[0.07]"
          : "border-white/10 bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]"
      }`}
    >
      <Group justify="space-between" gap="xs" wrap="nowrap">
        <Group gap="xs" wrap="nowrap" className="min-w-0">
          <Badge
            size="lg"
            radius="xl"
            color={selected ? "brand" : "gray"}
            variant={selected ? "filled" : "light"}
            className="shrink-0"
          >
            {route.name.replace("Route ", "")}
          </Badge>
          <Text size="sm" fw={600} c="white" className="route-name truncate">
            {route.name}
          </Text>
        </Group>
        <Group gap={4} wrap="nowrap" justify="flex-end">
          {route.tags.includes("Recommended") && (
            <Badge size="sm" radius="xl" color="brand" variant="light" leftSection={<Sparkles size={9} />}>
              Best
            </Badge>
          )}
          {route.tags.includes("Fastest") && (
            <Badge size="sm" radius="xl" color="gray" variant="light" leftSection={<Clock size={9} />}>
              Fastest
            </Badge>
          )}
          {route.tags.includes("All-clear") && !route.is_recommended && (
            <Badge size="sm" radius="xl" color="teal" variant="light" leftSection={<Check size={9} />}>
              Clear
            </Badge>
          )}
        </Group>
      </Group>

      <Text size="sm" c="dimmed" className="mt-1.5 truncate">
        {route.description}
      </Text>

      <Group grow gap="xs" className="mt-3">
        {[
          [formatMiles(route.distance_miles), "miles"],
          [formatDuration(route.duration_minutes), "drive"],
          [route.risk.avg_risk.toFixed(2), "avg risk"],
        ].map(([value, label]) => (
          <div key={label}>
            <Text size="lg" fw={600} lh={1} c="white">
              {value}
            </Text>
            <Text size="sm" tt="uppercase" c="dimmed" className="mt-1 tracking-[0.12em]">
              {label}
            </Text>
          </div>
        ))}
      </Group>

      <Progress.Root size="sm" radius="xl" mt="sm" className="route-exposure">
        {segments.map((key) => (
          <Progress.Section
            key={key}
            value={((route.risk.miles[key] ?? 0) / totalMiles) * 100}
            style={{ backgroundColor: RISK_COLORS[key] }}
            aria-label={`${formatMiles(route.risk.miles[key] ?? 0)} miles ${RISK_LABELS[key]}`}
          />
        ))}
      </Progress.Root>
      <Group justify="space-between" mt={5}>
        <Text size="sm" c="dimmed">
          {route.risk.no_travel_miles > 0 ? "No-travel segment" : "Risk exposure"}
        </Text>
        <Text size="sm" c="dimmed">
          {formatMiles(route.risk.severe_miles)} mi severe+
        </Text>
      </Group>

      <Group justify="space-between" mt="xs" pt="xs" className="border-t border-white/5">
        <Text size="sm" c="dimmed">
          Arrive <Text span fw={600} c="white">{formatClockWithZone(route.eta)}</Text>
        </Text>
        <Badge
          size="sm"
          radius="xl"
          variant="light"
          styles={{
            root: {
              color: RISK_COLORS[level],
              backgroundColor: `${RISK_COLORS[level]}14`,
              borderColor: `${RISK_COLORS[level]}33`,
            },
          }}
          leftSection={<i className="h-1.5 w-1.5 rounded-full" style={{ background: RISK_COLORS[level] }} />}
        >
          {riskLabel(level)}
        </Badge>
      </Group>
    </Paper>
  );
}
