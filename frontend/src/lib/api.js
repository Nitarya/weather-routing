class ApiError extends Error {
  constructor(message, status = 500, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
async function request(url, init) {
  let response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.body ? { "Content-Type": "application/json" } : {}
      }
    });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
  }
  if (!response.ok) {
    throw new ApiError(
      payload?.error?.message ?? `Request failed (${response.status}).`,
      response.status,
      payload?.error?.code
    );
  }
  return payload;
}
function fetchConfig() {
  return request("/api/config/");
}
function planTrip(payload) {
  return request("/api/plan/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
async function fetchReverseGeocode(lat, lng) {
  const payload = await request(
    `/api/reverse-geocode/?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`
  );
  return payload?.area ?? "";
}
function fetchHeatmap(payload) {
  return request("/api/heatmap/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
export {
  ApiError,
  fetchConfig,
  fetchHeatmap,
  fetchReverseGeocode,
  planTrip
};
