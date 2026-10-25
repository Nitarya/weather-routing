import { Loader, Paper, Text, Title } from "@mantine/core";

export function WeatherLoader({ active, mode, interval }) {
  if (!active) return null;

  return (
    <div
      className="weather-loader fixed inset-0 z-[100] grid place-items-center bg-ink-950/80 p-6 backdrop-blur-md"
      role="status"
      aria-live="polite"
    >
      <Paper
        withBorder
        radius="lg"
        px="xl"
        py="lg"
        className="weather-loader-card w-full max-w-[440px] border-brand/30 bg-ink-900/95 text-center shadow-2xl"
      >
        <Loader size={64} color="brand" type="oval" className="mx-auto mb-4" />
        <Text size="sm" fw={600} tt="uppercase" c="brand" className="tracking-[0.18em]">
          Google Weather
        </Text>
        <Title order={2} size="h3" mt={4} c="white">
          {mode === "plan" ? "Fetching weather" : "Building 48-hour weather"}
        </Title>
        <Text size="sm" c="dimmed" maw={330} mx="auto" mt={8} lh={1.55}>
          {mode === "plan"
            ? `Sampling every ${interval} miles at each checkpoint's estimated arrival time.`
            : "Scoring every checkpoint and every hour from departure through +48 hours."}
        </Text>
        <div
          className="mx-auto mt-5 h-1 max-w-[260px] overflow-hidden rounded-full bg-white/10"
          aria-hidden="true"
        >
          <span className="block h-full w-2/5 animate-[weather-progress_1.3s_ease-in-out_infinite] rounded-full bg-brand" />
        </div>
      </Paper>
    </div>
  );
}
