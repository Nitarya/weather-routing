import { RISK_COLORS, RISK_LEVELS } from "../constants";
function rgba(hex, alpha) {
  const value = hex.replace("#", "");
  const bigint = parseInt(value, 16);
  const r = bigint >> 16 & 255;
  const g = bigint >> 8 & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
class HeatmapOverlay {
  map;
  overlay = null;
  canvas = null;
  context = null;
  cells = [];
  hour = 0;
  spacingMiles = 18;
  width = 0;
  height = 0;
  dpr = 1;
  order = [];
  idleListener = null;
  constructor(map) {
    this.map = map;
    const overlay = new google.maps.OverlayView();
    const canvas = document.createElement("canvas");
    canvas.className = "heatmap-canvas absolute left-0 top-0 z-[2] pointer-events-none opacity-90 blur-[8px] saturate-150";
    canvas.setAttribute("aria-hidden", "true");
    overlay.onAdd = () => {
      const panes = overlay.getPanes();
      if (panes) panes.overlayLayer.appendChild(canvas);
    };
    overlay.draw = () => {
      this.syncSize();
      this.render();
    };
    overlay.onRemove = () => {
      canvas.remove();
      this.canvas = null;
      this.context = null;
    };
    overlay.setMap(map);
    this.overlay = overlay;
    this.canvas = canvas;
    this.idleListener = map.addListener("idle", () => this.render());
  }
  setData(cells, spacingMiles) {
    this.cells = cells;
    this.spacingMiles = spacingMiles;
    this.hour = Math.min(this.hour, Math.max(0, (cells[0]?.risks.length ?? 1) - 1));
    this.rebuildOrder();
    this.render();
  }
  setHour(hour) {
    this.hour = hour;
    this.rebuildOrder();
    this.render();
  }
  clear() {
    this.cells = [];
    this.render();
  }
  destroy() {
    if (this.idleListener && window.google?.maps?.event) {
      window.google.maps.event.removeListener(this.idleListener);
    }
    this.idleListener = null;
    this.overlay?.setMap(null);
    this.overlay = null;
    this.canvas = null;
  }
  rebuildOrder() {
    this.order = this.cells.map((cell, index) => ({ index, risk: cell.risks[this.hour] ?? 0 })).sort((a, b) => a.risk - b.risk).map((entry) => entry.index);
  }
  syncSize() {
    if (!this.canvas || !this.overlay) return;
    const div = this.map.getDiv();
    const width = div.clientWidth;
    const height = div.clientHeight;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (!width || !height) return;
    if (this.width !== width || this.height !== height || this.dpr !== dpr) {
      this.width = width;
      this.height = height;
      this.dpr = dpr;
      this.canvas.width = Math.round(width * dpr);
      this.canvas.height = Math.round(height * dpr);
      this.canvas.style.width = `${width}px`;
      this.canvas.style.height = `${height}px`;
      const context = this.canvas.getContext("2d");
      this.context = context;
    }
  }
  render() {
    const context = this.context;
    const canvas = this.canvas;
    if (!context || !canvas) return;
    const ctx = context;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    if (this.cells.length === 0 || !this.overlay) return;
    const projection = this.overlay.getProjection();
    const center = this.map.getCenter();
    if (!projection || !center) return;
    const centerPoint = projection.fromLatLngToDivPixel(center);
    if (!centerPoint) return;
    const originX = centerPoint.x - this.width / 2;
    const originY = centerPoint.y - this.height / 2;
    canvas.style.left = `${originX}px`;
    canvas.style.top = `${originY}px`;
    const latitudeStep = this.spacingMiles / 69;
    const northPoint = projection.fromLatLngToDivPixel(
      new google.maps.LatLng(center.lat() + latitudeStep, center.lng())
    );
    const geoRadius = northPoint ? Math.abs(northPoint.y - centerPoint.y) * 1.75 : 14;
    const radius = Math.max(14, Math.min(60, geoRadius));
    for (const index of this.order) {
      const cell = this.cells[index];
      const risk = cell.risks[this.hour] ?? 0;
      // Low-risk cells are intentionally not painted. Otherwise the whole
      // corridor is a permanent cyan cloud and the slider has no visible effect.
      if (risk <= 0) continue;
      const point = projection.fromLatLngToDivPixel(
        new google.maps.LatLng(cell.lat, cell.lng)
      );
      if (!point) continue;
      const x = point.x - originX;
      const y = point.y - originY;
      if (x < -radius || y < -radius || x > this.width + radius || y > this.height + radius) {
        continue;
      }
      const color = RISK_COLORS[RISK_LEVELS[risk] ?? "low"];
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
      gradient.addColorStop(0, rgba(color, risk >= 2 ? 0.72 : 0.58));
      gradient.addColorStop(0.5, rgba(color, risk >= 2 ? 0.4 : 0.3));
      gradient.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
export {
  HeatmapOverlay
};
