import "@fontsource-variable/inter";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createTheme, MantineProvider } from "@mantine/core";
import { DatesProvider } from "@mantine/dates";
import App from "./App";
import "./index.css";

const theme = createTheme({
  fontFamily: '"Inter Variable", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  primaryColor: "brand",
  primaryShade: 6,
  defaultRadius: "md",
  colors: {
    dark: [
      "#d7e8ea",
      "#aac6c9",
      "#7fa4a9",
      "#5a858b",
      "#3d6a72",
      "#0a2831",
      "#08222b",
      "#061d26",
      "#041820",
      "#031118",
    ],
    brand: [
      "#e6fffb",
      "#c8fff7",
      "#9ff8ed",
      "#6ff5e5",
      "#4cebdc",
      "#40e0d0",
      "#2fc6b7",
      "#219f94",
      "#167b73",
      "#0b5752",
    ],
  },
  components: {
    TextInput: {
      defaultProps: { variant: "default", size: "md" },
    },
    NumberInput: {
      defaultProps: { variant: "default", size: "md" },
    },
    DateTimePicker: {
      defaultProps: { variant: "default", size: "md" },
    },
    SegmentedControl: {
      defaultProps: { color: "brand", size: "sm" },
    },
    Slider: {
      defaultProps: { color: "brand" },
    },
  },
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <DatesProvider settings={{ locale: "en" }}>
        <App />
      </DatesProvider>
    </MantineProvider>
  </StrictMode>,
);
