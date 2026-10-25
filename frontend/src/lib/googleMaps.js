let loaderPromise = null;
function loadGoogleMaps(apiKey) {
  if (window.google?.maps?.Map) return Promise.resolve(window.google);
  if (loaderPromise) return loaderPromise;
  if (!apiKey) {
    return Promise.reject(new Error("No Google Maps API key is configured."));
  }
  loaderPromise = new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      loaderPromise = null;
      reject(new Error("Google Maps did not finish loading. Check the API key restrictions."));
    }, 15e3);
    window.__spotterMapsLoaded = () => {
      window.clearTimeout(timeout);
      if (window.google?.maps) resolve(window.google);
      else reject(new Error("Google Maps loaded without the expected API."));
    };
    const script = document.createElement("script");
    script.async = true;
    script.defer = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(
      apiKey
    )}&v=weekly&libraries=geometry&loading=async&callback=__spotterMapsLoaded`;
    script.onerror = () => {
      window.clearTimeout(timeout);
      loaderPromise = null;
      reject(new Error("Google Maps failed to load. Check your network connection."));
    };
    document.head.appendChild(script);
  });
  return loaderPromise;
}
const DARK_MAP_STYLES = [
  { elementType: "geometry", stylers: [{ color: "#071c24" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#6e9097" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#04151c" }] },
  {
    featureType: "administrative",
    elementType: "geometry.stroke",
    stylers: [{ color: "#123640" }]
  },
  {
    featureType: "administrative.country",
    elementType: "geometry.stroke",
    stylers: [{ color: "#1a4b55" }]
  },
  {
    featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#a7c4c9" }]
  },
  {
    featureType: "administrative.province",
    elementType: "labels.text.fill",
    stylers: [{ color: "#7b9ca3" }]
  },
  {
    featureType: "landscape.natural",
    elementType: "geometry",
    stylers: [{ color: "#08232c" }]
  },
  {
    featureType: "landscape.man_made",
    elementType: "geometry",
    stylers: [{ color: "#08222a" }]
  },
  {
    featureType: "poi",
    stylers: [{ visibility: "off" }]
  },
  {
    featureType: "poi.park",
    elementType: "geometry",
    stylers: [{ color: "#0a2b31" }]
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#10333d" }]
  },
  {
    featureType: "road",
    elementType: "labels.text.fill",
    stylers: [{ color: "#50757d" }]
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#17505a" }]
  },
  {
    featureType: "road.highway",
    elementType: "geometry.stroke",
    stylers: [{ color: "#0b2c34" }]
  },
  {
    featureType: "road.highway",
    elementType: "labels.text.fill",
    stylers: [{ color: "#7fa7ad" }]
  },
  {
    featureType: "transit",
    stylers: [{ visibility: "off" }]
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#031b24" }]
  },
  {
    featureType: "water",
    elementType: "labels.text.fill",
    stylers: [{ color: "#3d6a74" }]
  }
];
export {
  DARK_MAP_STYLES,
  loadGoogleMaps
};
