import { jsx, jsxs } from "react/jsx-runtime";
function base({ size = 18, ...props }) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    ...props
  };
}
function ArrowRight(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "M5 12h14M13 6l6 6-6 6" }) });
}
function SwapVertical(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "M8 4v14M4 14l4 4 4-4M16 20V6M12 10l4-4 4 4" }) });
}
function MapPin(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M20 10c0 5.5-8 12-8 12s-8-6.5-8-12a8 8 0 1 1 16 0Z" }),
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "10", r: "2.7" })
  ] });
}
function Clock(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "8.5" }),
    /* @__PURE__ */ jsx("path", { d: "M12 7.5V12l3 2" })
  ] });
}
function Weight(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M6.5 8h11l2.2 10.5a1.8 1.8 0 0 1-1.8 2.2H6.1a1.8 1.8 0 0 1-1.8-2.2L6.5 8Z" }),
    /* @__PURE__ */ jsx("path", { d: "M9 8a3 3 0 1 1 6 0" })
  ] });
}
function Calendar(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("rect", { x: "3.5", y: "5", width: "17", height: "15.5", rx: "2.5" }),
    /* @__PURE__ */ jsx("path", { d: "M3.5 10h17M8 3v4M16 3v4" })
  ] });
}
function Play(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), fill: "currentColor", stroke: "none", children: /* @__PURE__ */ jsx("path", { d: "M8 5.8v12.4c0 .8.9 1.3 1.6.9l9.5-6.2c.6-.4.6-1.4 0-1.8L9.6 4.9A1 1 0 0 0 8 5.8Z" }) });
}
function Pause(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), fill: "currentColor", stroke: "none", children: [
    /* @__PURE__ */ jsx("rect", { x: "6.5", y: "5", width: "3.6", height: "14", rx: "1" }),
    /* @__PURE__ */ jsx("rect", { x: "13.9", y: "5", width: "3.6", height: "14", rx: "1" })
  ] });
}
function Layers(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "m12 3 9 5-9 5-9-5 9-5Z" }),
    /* @__PURE__ */ jsx("path", { d: "m3 12 9 5 9-5M3 16l9 5 9-5" })
  ] });
}
function Info(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "8.7" }),
    /* @__PURE__ */ jsx("path", { d: "M12 11v5M12 7.7v.2" })
  ] });
}
function Close(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "m6.5 6.5 11 11m0-11-11 11" }) });
}
function Wind(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "M3.5 8.5h9a3 3 0 1 0-3-3M3.5 12.5h14a2.8 2.8 0 1 1-2.8 2.8M3.5 16.5h5" }) });
}
function Rain(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M7 14.5a4 4 0 1 1 1-7.9A5.2 5.2 0 0 1 18 8.6a3 3 0 0 1 .3 5.9" }),
    /* @__PURE__ */ jsx("path", { d: "M8.5 17.5 7.5 20M12.5 17.5l-1 2.5M16.5 17.5l-1 2.5" })
  ] });
}
function Snow(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M12 3v18M4.2 7.5l15.6 9M19.8 7.5l-15.6 9" }),
    /* @__PURE__ */ jsx("path", { d: "M9.4 4.8 12 7.2l2.6-2.4M9.4 19.2 12 16.8l2.6 2.4" })
  ] });
}
function Thermometer(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M10 13.8V5a2 2 0 1 1 4 0v8.8a4.2 4.2 0 1 1-4 0Z" }),
    /* @__PURE__ */ jsx("path", { d: "M12 9v6" })
  ] });
}
function ChevronDown(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "m6 9.5 6 6 6-6" }) });
}
function Sparkles(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M12 3.5 13.6 8l4.4 1.6-4.4 1.6L12 15.7l-1.6-4.5L6 9.6 10.4 8 12 3.5Z" }),
    /* @__PURE__ */ jsx("path", { d: "M18.5 14.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2ZM5 3l.6 1.7L7.3 5.3l-1.7.6L5 7.6l-.6-1.7-1.7-.6 1.7-.6L5 3Z" })
  ] });
}
function Warning(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M12 3.7 21 20H3L12 3.7Z" }),
    /* @__PURE__ */ jsx("path", { d: "M12 9v5M12 17.2v.2" })
  ] });
}
function Check(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "m5 12.5 4.5 4.5L19 7" }) });
}
function Search(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "10.8", cy: "10.8", r: "6.8" }),
    /* @__PURE__ */ jsx("path", { d: "m16 16 4.2 4.2" })
  ] });
}
function RouteIcon(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "6", cy: "18", r: "2.4" }),
    /* @__PURE__ */ jsx("circle", { cx: "18", cy: "6", r: "2.4" }),
    /* @__PURE__ */ jsx("path", { d: "M8.4 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.6" })
  ] });
}
function Gauge(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("path", { d: "M4.2 18a9 9 0 1 1 15.6 0" }),
    /* @__PURE__ */ jsx("path", { d: "M12 13.5 15.8 9" }),
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "14", r: "1.5" })
  ] });
}
function Radar(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "8.6" }),
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "4.4" }),
    /* @__PURE__ */ jsx("path", { d: "M12 12 18.2 6M12 3.4v1.8M12 18.8v1.8M3.4 12h1.8M18.8 12h1.8" })
  ] });
}
function CloudIcon(props) {
  return /* @__PURE__ */ jsx("svg", { ...base(props), children: /* @__PURE__ */ jsx("path", { d: "M6.8 17.5a4 4 0 1 1 1-7.9A5.2 5.2 0 0 1 18 11.2a3.2 3.2 0 0 1-.4 6.3H6.8Z" }) });
}
function SunIcon(props) {
  return /* @__PURE__ */ jsxs("svg", { ...base(props), children: [
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "4" }),
    /* @__PURE__ */ jsx("path", { d: "M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M18.5 5.5l-1.4 1.4M6.9 17.1l-1.4 1.4" })
  ] });
}
function WeatherGlyph({ condition, size = 16 }) {
  if (condition === "snow") return /* @__PURE__ */ jsx(Snow, { size });
  if (condition === "rain" || condition === "drizzle" || condition === "storm")
    return /* @__PURE__ */ jsx(Rain, { size });
  if (condition === "fog") return /* @__PURE__ */ jsx(CloudIcon, { size });
  if (condition === "windy") return /* @__PURE__ */ jsx(Wind, { size });
  if (condition === "clear" || condition === "mostly_clear") return /* @__PURE__ */ jsx(SunIcon, { size });
  return /* @__PURE__ */ jsx(CloudIcon, { size });
}
export {
  ArrowRight,
  Calendar,
  Check,
  ChevronDown,
  Clock,
  Close,
  CloudIcon,
  Gauge,
  Info,
  Layers,
  MapPin,
  Pause,
  Play,
  Radar,
  Rain,
  RouteIcon,
  Search,
  Snow,
  Sparkles,
  SunIcon,
  SwapVertical,
  Thermometer,
  Warning,
  WeatherGlyph,
  Weight,
  Wind
};
