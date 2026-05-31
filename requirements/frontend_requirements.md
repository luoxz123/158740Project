# Frontend Requirements

The frontend shall provide a professional WebGIS interface for renewable energy planning in New Zealand.

## Required Features

- Leaflet map with OpenStreetMap basemap.
- Layer toggles for wind suitability, solar suitability, transmission lines, road access corridors, protected areas, GIR points, weather resource points, recommended sites, and heatmap.
- Search over region names, place names, candidate sites, road classes, article titles, and energy types.
- Popup information for each layer.
- Dashboard charts using Chart.js.
- Legend panel.
- Suitability filters by energy type and minimum score.
- GeoServer WMS switch using the `renewable_nz` workspace.
- Responsive layout for desktop and mobile browser widths.

## Frontend Files

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`
- `frontend/data/*.geojson`
