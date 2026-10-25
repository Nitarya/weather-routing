# Route Weather

Weather-aware truck routing proof of concept built with React, Django, Google Maps
Platform and Mantine.

## What it does

1. Accepts an origin, destination, departure time and load weight.
2. Fetches up to three traffic-aware truck routes from Google Routes API.
3. Samples each route every **10, 25 or 50 miles**.
4. Looks up Google Weather hourly data at every checkpoint's ETA.
5. Applies wind/rain/snow thresholds plus load overrides.
6. Ranks the routes and recommends the safest one.
7. Draws the routes, checkpoints, ETAs and risk levels on Google Maps.
8. Builds a **0–48 hour** weather-risk heatmap for the selected route.

No caching: every analysis calls Google again.

## Stack

- React 19 + Vite
- Tailwind CSS 4 for layout
- Mantine 9 for inputs, date-time picker, cards, badges, loaders and the heatmap slider
- Django 5.2
- Google Geocoding API
- Google Routes API (`computeRoutes`, traffic-aware)
- Google Weather API (`forecast/hours:lookup`)
- Google Maps JavaScript API

## Run locally

Requirements: Python 3.12+, Node 20+, and a Google Cloud key with Geocoding, Routes,
Weather and Maps JavaScript APIs enabled.

```bash
cp .env.example .env
# set GOOGLE_MAPS_API_KEY and APP_PASSWORD in .env

python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

cd frontend
npm ci
npm run build
cd ..

cd backend
../.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000.

For frontend hot reload, run `npm run dev` in `frontend/` and Django separately; Vite proxies
`/api` to `127.0.0.1:8000`.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `GOOGLE_MAPS_API_KEY` | yes | Geocoding, Routes, Weather and Maps JS |
| `APP_PASSWORD` | public deployment | Shared Basic Auth password |
| `APP_USERNAME` | no | Basic Auth username; defaults to `route` |
| `DJANGO_SECRET_KEY` | production | Django secret |
| `DJANGO_DEBUG` | no | `true` locally |
| `DJANGO_ALLOWED_HOSTS` | production | Comma-separated hosts |

### Access protection

The app and all `/api/` routes are protected by HTTP Basic Auth when
`APP_PASSWORD` is set. The browser prompts for the username (`route` by default)
and password before loading the React app, so no Maps or Google API requests are
made before authentication. `/api/health/` remains public for hosting health
checks and does not call any billable Google API.

If `APP_PASSWORD` is empty:

- local `DJANGO_DEBUG=true` runs remain open for development;
- production (`DJANGO_DEBUG=false`) refuses to serve with `503`, so a public
  deployment cannot accidentally be left unprotected.

Use HTTPS in production; Basic Auth sends the password with each request.

## HTTP API

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health/` | Liveness and key status |
| GET | `/api/config/` | Maps key, sample intervals, forecast hours |
| GET | `/api/reverse-geocode/` | Area label for a checkpoint coordinate |
| POST | `/api/plan/` | Routes, checkpoints, risk and recommendation |
| POST | `/api/heatmap/` | Selected-route 0–48h heatmap |

### Plan request

```json
{
  "origin": "Dallas, TX",
  "destination": "Denver, CO",
  "departure_time": "2026-10-25T12:30:00.000Z",
  "load_lb": 44000,
  "sample_interval_miles": 25
}
```

### Heatmap request

```json
{
  "polyline": "...",
  "departure_time": "2026-10-25T12:30:00.000Z",
  "load_lb": 44000,
  "hours": 48
}
```

## Backend structure

```text
backend/
  config/
    settings.py          Environment, Google API settings, static files
    urls.py              URL routes
    wsgi.py / asgi.py    Deployment entry points
  routing/
    views.py             HTTP endpoints and SPA shell
    services/
      geocoding.py       Google Geocoding; text -> coordinates
      google_routes.py   Google Routes API; routes -> RouteOption objects
      weather.py         Google Weather; checkpoint/page/unit handling
      polyline.py        Decode, distance, interpolation and sampling
      risk.py            Wind/rain/snow thresholds and load overrides
      planner.py         Plan orchestration, checkpoint risk and ranking
      heatmap.py         Corridor grid and hourly risk matrix
    tests/               54 unit/API/auth tests
  templates/             SPA shell and dev fallback
```

### Backend functions

| File | Main functions |
| --- | --- |
| `views.py` | `index`, `health`, `config`, `plan`, `heatmap` |
| `geocoding.py` | `geocode_address` (Google Geocoding), `resolve_location` |
| `google_routes.py` | `fetch_routes`, `_fetch_routes`, `_payload`, `_call_routes`, `_to_option` |
| `weather.py` | `fetch_weather`, `_fetch_point`, `_fetch_page`, `_normalise`, `weather_at`, `nearest_hour_index`, unit converters |
| `polyline.py` | `decode_polyline`, `haversine_miles`, `cumulative_distances`, `interpolate`, `sample_route`, `bounding_box` |
| `risk.py` | `classify_wind`, `classify_rain`, `classify_snow`, `assess_weather`, `risk_meta` |
| `planner.py` | `parse_departure`, `_build_checkpoints`, `_summarise_risk`, `_route_sort_key`, `_recommendation_reason`, `build_plan` |
| `heatmap.py` | `_corridor_cells`, `_build_cells`, `build_heatmap` |

### Plan flow

```text
POST /api/plan/
  -> resolve origin/destination via Geocoding
  -> fetch_routes() via Routes API
  -> sample_route() at selected interval
  -> fetch_weather() for all checkpoint coordinates
  -> assess_weather() per checkpoint with load overrides
  -> _summarise_risk() distance-weighted risk miles
  -> rank routes and build recommendation
```

Weather sampling is exact: every 10/25/50-mile checkpoint gets its own Google Weather
lookup at the nearest hourly forecast to its ETA.

### Heatmap flow

```text
POST /api/heatmap/
  -> decode selected route polyline
  -> build a route-hugging ~30-mile corridor grid
  -> fetch weather for every cell
  -> score all cells for hours 0..48
  -> return risk codes, summary and time labels
```

Only moderate/high/severe/no-travel cells are painted, so the low-risk corridor is not a
permanent cyan wash. If an hour has no elevated-risk cells, the UI says so.

## Frontend structure

```text
frontend/
  src/
    main.jsx             Mantine provider, dark theme, DatesProvider
    App.jsx              Page state, plan/heatmap orchestration, layout
    components/
      Sidebar.jsx        Form, local Autocomplete, date picker, route results
      MapView.jsx        Google map, route lines, markers, InfoWindows, heatmap
      HeatmapControls.jsx  Mantine Slider + risk legend
      RouteCard.jsx      Route summary, badges and risk-exposure bar
      CheckpointPanel.jsx  Scrollable checkpoint list
      TripSummary.jsx    Selected-route summary overlay
      WeatherLoader.jsx  Full-screen weather loading state
      Risk.jsx           Risk dot and legend
      Logo.jsx           Neutral RouteWeather wordmark
      Icons.jsx          Inline SVG icons
    lib/
      api.js             fetchConfig, planTrip, fetchHeatmap
      format.js          Clock, duration, miles, weight and date formatting
      geo.js             Polyline decoding
      googleMaps.js      Maps JS loader
      heatmapOverlay.js  Canvas heatmap overlay
    data/locations.json  168 local autocomplete locations
    constants.js         Risk labels and colors
    index.css            Tailwind + Mantine layers and map/InfoWindow rules
  index.html
  vite.config.js
```

### Frontend functions

| File | Main responsibility |
| --- | --- |
| `App.jsx` | Form submission, plan request, selected route, heatmap request, hour state, focus state |
| `Sidebar.jsx` | Controlled form, local location filtering, Mantine controls, route list |
| `MapView.jsx` | Loads Google Maps; draws all route polylines, selected-route emphasis, endpoint/checkpoint markers and risk popups; connects the canvas heatmap |
| `HeatmapControls.jsx` | 0–48h Mantine Slider, current hour/risk summary, legend |
| `RouteCard.jsx` | Route metrics, ETA, recommendation/fastest/clear badges, risk exposure |
| `CheckpointPanel.jsx` | Lists every checkpoint with ETA, mile, weather and risk |
| `TripSummary.jsx` | Selected route summary over the map |
| `WeatherLoader.jsx` | Full-screen loading overlay for plans and heatmaps |
| `heatmapOverlay.js` | Projects corridor cells onto Google Maps and paints elevated-risk cells |
| `api.js` | Small JSON client with consistent error handling |

## Weather and risk details

### Sampling

- Checkpoints are placed every selected interval, including origin and destination.
- Weather uses the hourly Google forecast nearest to each checkpoint ETA.
- Google returns 24 hours per request; the backend pages only as far as needed.
- Google `snowQpf` is liquid-water equivalent; a 10:1 ratio approximates snow depth.

### Risk thresholds

| Condition | Low | Moderate | High | Severe | No Travel |
| --- | --- | --- | --- | --- | --- |
| Wind | < 25 mph | 25–34 | 35–44 | 45–54 | ≥ 55 |
| Rain | < 0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 |
| Snow | < 0.5 in/hr | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | > 3.0 |

Load overrides:

- ≥ 55 mph → No Travel for any load
- 45–54 mph + > 30,000 lb → No Travel
- 35–44 mph + > 40,000 lb → Severe

### Recommendation order

1. Fewest severe-weather miles (No Travel counts as severe)
2. Fewest high-risk miles
3. Lowest distance-weighted average risk
4. Shortest travel time

## Tests

```bash
cd backend
../.venv/bin/python manage.py test routing
```

The suite covers risk thresholds, load overrides, Basic Auth, polyline sampling, planner validation,
ranking, Weather API normalization/pagination, heatmap construction and API contracts.

## Docker deployment with Nginx

The `Dockerfile` builds the React app and serves it from Django with Gunicorn +
WhiteNoise. `docker-compose.yml` runs only the app container; Nginx on the host
terminates TLS and proxies to it.

### 1. VM and `.env`

Open ports 80/443 in the firewall, install Docker Engine + Compose, and copy the
project to the VM. Then:

```bash
cp .env.example .env
```

Set:

```env
GOOGLE_MAPS_API_KEY=...
APP_USERNAME=route
APP_PASSWORD=use-a-strong-password
DJANGO_SECRET_KEY=<openssl rand -hex 32>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your-domain.example
```

### 2. Run the app

```bash
docker compose up -d --build
docker compose ps
```

The app binds only to `127.0.0.1:8000`; it is not publicly exposed.

```bash
curl -s http://127.0.0.1:8000/api/health/   # 200
```

### 3. Nginx reverse proxy

Create `/etc/nginx/sites-available/route-weather`:

```nginx
server {
    listen 80;
    server_name route.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name route.example.com;

    ssl_certificate /etc/letsencrypt/live/route.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/route.example.com/privkey.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header Authorization $http_authorization;
        proxy_read_timeout 180s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/route-weather /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Issue a certificate if needed:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d route.example.com
```

### 4. Verify

```bash
curl https://route.example.com/api/health/             # 200, public
curl -I https://route.example.com/                      # 401
curl -u route:YOUR_PASSWORD https://route.example.com/  # 200
```

### 5. Update

```bash
docker compose up -d --build
```

`render.yaml` is also included as an alternative deployment target.
