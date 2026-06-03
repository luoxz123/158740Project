const CONFIG = {
  nzBounds: [[-47.6, 165.5], [-34.0, 179.5]],
  geoserverWmsUrl: window.APP_CONFIG?.geoserverWmsUrl || "http://localhost:8080/geoserver/renewable_nz/wms",
  geoserverLayers: {
    wind: "renewable_nz:wind_suitability",
    solar: "renewable_nz:solar_suitability",
    transmission: "renewable_nz:transmission_lines",
    roads: "renewable_nz:roads",
    protected: "renewable_nz:protected_areas",
    gir: "renewable_nz:gir_locations",
    weather: "renewable_nz:weather_resource_summary",
    siteSelection: "renewable_nz:site_selection_candidates"
  },
  dataFiles: {
    wind: "data/wind_suitability.geojson",
    solar: "data/solar_suitability.geojson",
    transmission: "data/transmission_lines.geojson",
    roads: "data/roads.geojson",
    protected: "data/protected_areas.geojson",
    gir: "data/gir_mentions.geojson",
    weather: "data/weather_resource_summary.geojson",
    siteSelection: "data/site_selection_candidates.geojson"
  }
};

const state = {
  data: {},
  localLayers: {},
  wmsLayers: {},
  rankLayer: null,
  heatLayer: null,
  charts: {},
  filters: {
    energy: "all",
    minScore: 70
  },
  visible: {
    wind: true,
    solar: true,
    transmission: true,
    roads: true,
    protected: true,
    gir: true,
    weather: true,
    siteSelection: true,
    heat: false
  },
  useWms: false
};

const map = L.map("map", {
  zoomControl: false,
  minZoom: 5
}).setView([-41.2, 172.7], 6);

L.control.zoom({ position: "bottomleft" }).addTo(map);

const basemap = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors"
});
basemap.addTo(map);

const panes = {
  protected: map.createPane("protected-pane"),
  suitability: map.createPane("suitability-pane"),
  network: map.createPane("network-pane"),
  points: map.createPane("points-pane")
};
panes.protected.style.zIndex = 360;
panes.suitability.style.zIndex = 390;
panes.network.style.zIndex = 430;
panes.points.style.zIndex = 460;

function scoreColor(score, type) {
  if (type === "solar") {
    if (score >= 85) return "#d58b18";
    if (score >= 70) return "#efc15c";
    return "#f2dfaa";
  }
  if (score >= 85) return "#5a6fb0";
  if (score >= 70) return "#8ca0d3";
  return "#c9d1ea";
}

function getFeatureCenter(feature) {
  const temp = L.geoJSON(feature);
  const bounds = temp.getBounds();
  return bounds.isValid() ? bounds.getCenter() : null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function titleCase(value) {
  return String(value || "n/a").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "n/a";
  return number.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function formatOptionalNumber(value, digits = 2, suffix = "") {
  const formatted = formatNumber(value, digits);
  return formatted === "n/a" ? formatted : `${formatted}${suffix}`;
}

function popupRows(metrics) {
  return metrics
    .map(([key, value]) => `<span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong>`)
    .join("");
}

function siteSelectionPopupContent(properties) {
  const energy = properties.energy_type || "site";
  const isSolar = energy === "solar";
  const title = properties.candidate_name || "Recommended site";
  const resourceRows = isSolar
    ? [
        ["Shortwave radiation", formatOptionalNumber(properties.total_shortwave_radiation_kwh_m2, 1, " kWh/m2")],
        ["Sunshine hours", formatOptionalNumber(properties.total_sunshine_hours, 1)]
      ]
    : [
        ["Mean wind speed 100 m", formatOptionalNumber(properties.mean_wind_speed_100m_ms, 2, " m/s")],
        ["P90 wind speed 100 m", formatOptionalNumber(properties.p90_wind_speed_100m_ms, 2, " m/s")]
      ];

  const metrics = [
    ["Rank", properties.rank || "n/a"],
    ["Energy type", titleCase(energy)],
    ["Region", properties.region || "n/a"],
    ["Final score", formatNumber(properties.final_score, 2)],
    ["Weather resource score", formatNumber(properties.weather_resource_score, 2)],
    ["Grid connection score", formatNumber(properties.grid_connection_score, 2)],
    ["GIR evidence score", formatNumber(properties.gir_evidence_score, 2)],
    ["Distance to transmission", formatOptionalNumber(properties.distance_to_transmission_km, 2, " km")],
    ...resourceRows,
    ["GIR mentions nearby", properties.gir_mentions_nearby ?? "0"]
  ];

  return `
    <div class="site-popup ${isSolar ? "solar" : "wind"}">
      <div class="site-popup-title">${escapeHtml(title)}</div>
      <div class="site-popup-grid">${popupRows(metrics)}</div>
      <div class="site-popup-formula">
        <span>Score formula</span>
        <strong>${escapeHtml(properties.score_formula || "55% resource + 25% transmission proximity + 15% GIR evidence + 5% interpolation confidence")}</strong>
      </div>
    </div>
  `;
}

function popupContent(properties, type) {
  if (type === "roads") {
    const metrics = [
      ["Class", properties.road_class || "n/a"],
      ["Source", properties.data_source || "n/a"]
    ];
    return `
      <div class="popup-title">${escapeHtml(properties.name || properties.road_name || "Road corridor")}</div>
      <div class="popup-grid">${popupRows(metrics)}</div>
    `;
  }

  if (type === "siteSelection") {
    return siteSelectionPopupContent(properties);
  }

  if (type === "weather") {
    const windScore = Number(properties.wind_resource_score || 0);
    const solarScore = Number(properties.solar_resource_score || 0);
    const combinedScore = Math.round((windScore + solarScore) / 2);
    const label = properties.place_name || "Weather resource point";
    const chartId = `popup-chart-${Math.random().toString(36).slice(2)}`;
    const metrics = [
      ["Region", properties.region || "n/a"],
      ["Wind 100 m", properties.mean_wind_speed_100m_ms ? `${properties.mean_wind_speed_100m_ms} m/s` : "n/a"],
      ["P90 wind", properties.p90_wind_speed_100m_ms ? `${properties.p90_wind_speed_100m_ms} m/s` : "n/a"],
      ["Sunshine", properties.total_sunshine_hours ? `${properties.total_sunshine_hours} h` : "n/a"],
      ["Solar radiation", properties.total_shortwave_radiation_kwh_m2 ? `${properties.total_shortwave_radiation_kwh_m2} kWh/m2` : "n/a"]
    ];

    setTimeout(() => renderPopupChart(chartId, combinedScore, "weather"), 40);

    return `
      <div class="popup-title">${escapeHtml(label)}</div>
      <div class="popup-grid">${popupRows(metrics)}</div>
      <canvas id="${chartId}" class="popup-chart"></canvas>
    `;
  }

  const score = properties.suitability_score ?? properties.score ?? "n/a";
  const label = properties.region_name || properties.place_name || properties.name || "Location";
  const energy = properties.energy_type || type || "network";
  const chartId = `popup-chart-${Math.random().toString(36).slice(2)}`;

  const metrics = [
    ["Energy", energy],
    ["Score", score],
    ["Grid distance", properties.distance_to_grid_km ? `${properties.distance_to_grid_km} km` : "n/a"],
    ["Constraint", properties.constraint_level || properties.status || "n/a"]
  ];

  const chart = typeof score === "number" ? `<canvas id="${chartId}" class="popup-chart"></canvas>` : "";

  setTimeout(() => renderPopupChart(chartId, Number(score), energy), 40);

  return `
    <div class="popup-title">${escapeHtml(label)}</div>
    <div class="popup-grid">${popupRows(metrics)}</div>
    ${chart}
  `;
}

function renderPopupChart(canvasId, score, energy) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || Number.isNaN(score)) return;
  const barColor = energy === "solar" ? "#d58b18" : energy === "weather" ? "#6f8f3e" : "#5a6fb0";

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: [energy, "Remaining"],
      datasets: [{
        data: [score, Math.max(0, 100 - score)],
        backgroundColor: [barColor, "#dfe6e1"],
        borderWidth: 0
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false, min: 0, max: 100 },
        y: { display: false }
      }
    }
  });
}

function suitabilityStyle(feature) {
  const props = feature.properties || {};
  const type = props.energy_type;
  const score = props.suitability_score || 0;
  const active = passesSuitabilityFilter(props);

  return {
    pane: "suitability-pane",
    color: type === "solar" ? "#9b5f0c" : "#384d91",
    weight: active ? 2 : 1,
    fillColor: scoreColor(score, type),
    fillOpacity: active ? 0.62 : 0.12,
    opacity: active ? 0.95 : 0.25
  };
}

function transmissionStyle() {
  return {
    pane: "network-pane",
    color: "#6d4b2f",
    weight: 3,
    opacity: 0.82
  };
}

function roadStyle() {
  return {
    pane: "network-pane",
    color: "#8a8f77",
    weight: 2,
    opacity: 0.72,
    dashArray: "7 5"
  };
}

function protectedStyle() {
  return {
    pane: "protected-pane",
    color: "#b34d3d",
    weight: 1.4,
    dashArray: "5 4",
    fillColor: "#b34d3d",
    fillOpacity: 0.16
  };
}

function girPointStyle(feature) {
  const type = feature.properties.energy_type;
  return {
    pane: "points-pane",
    radius: 7,
    color: "#ffffff",
    weight: 1.5,
    fillColor: type === "solar" ? "#d58b18" : type === "wind" ? "#5a6fb0" : "#1b7f5a",
    fillOpacity: 0.95
  };
}

function girPoint(feature, latlng) {
  return L.circleMarker(latlng, girPointStyle(feature));
}

function weatherPointStyle(feature) {
  const props = feature.properties || {};
  const windScore = Number(props.wind_resource_score || 0);
  const solarScore = Number(props.solar_resource_score || 0);
  const combinedScore = Math.max(0, Math.min(100, (windScore + solarScore) / 2));

  return {
    pane: "points-pane",
    radius: 6 + combinedScore / 18,
    color: "#ffffff",
    weight: 1.5,
    fillColor: "#6f8f3e",
    fillOpacity: 0.9
  };
}

function weatherPoint(feature, latlng) {
  return L.circleMarker(latlng, weatherPointStyle(feature));
}

function siteSelectionPointStyle(feature) {
  const props = feature.properties || {};
  const score = Number(props.final_score || 0);
  const type = props.energy_type;

  return {
    pane: "points-pane",
    radius: 7 + score / 20,
    color: "#111827",
    weight: 1.7,
    fillColor: type === "solar" ? "#f4a62a" : "#4f67b1",
    fillOpacity: 0.96
  };
}

function siteSelectionPoint(feature, latlng) {
  return L.circleMarker(latlng, siteSelectionPointStyle(feature));
}

function siteRankIcon(feature) {
  const props = feature.properties || {};
  const type = props.energy_type === "solar" ? "solar" : "wind";
  return L.divIcon({
    className: "",
    iconSize: [34, 44],
    iconAnchor: [17, 44],
    popupAnchor: [0, -42],
    html: `
      <div class="site-rank-marker ${type}" title="${escapeHtml(titleCase(type))} recommended site rank ${escapeHtml(props.rank || "")}">
        <span>${escapeHtml(props.rank || "")}</span>
      </div>
    `
  });
}

function createSiteRankLayer() {
  const markers = (state.data.siteSelection.features || [])
    .filter((feature) => feature.geometry?.type === "Point")
    .map((feature) => {
      const [lng, lat] = feature.geometry.coordinates;
      const marker = L.marker([lat, lng], {
        icon: siteRankIcon(feature),
        pane: "points-pane",
        zIndexOffset: 900,
        riseOnHover: true
      });
      marker.feature = feature;
      marker.bindPopup(() => popupContent(feature.properties || {}, "siteSelection"), {
        minWidth: 305,
        maxWidth: 360
      });
      return marker;
    });

  state.rankLayer = L.layerGroup(markers);
}

function passesSuitabilityFilter(props) {
  const type = props.energy_type;
  const score = props.suitability_score || 0;
  const energyMatch = state.filters.energy === "all" || state.filters.energy === type;
  return energyMatch && score >= state.filters.minScore;
}

function bindCommonPopup(layer, type) {
  layer.bindPopup(() => popupContent(layer.feature.properties || {}, type), type === "siteSelection" ? {
    minWidth: 305,
    maxWidth: 360
  } : undefined);
  layer.on("mouseover", () => {
    if (!layer.setStyle) return;
    layer.setStyle({ weight: type === "gir" || type === "weather" ? 3 : 4 });
  });
  layer.on("mouseout", () => {
    if (layer.setStyle) {
      if (type === "transmission") layer.setStyle(transmissionStyle());
      else if (type === "roads") layer.setStyle(roadStyle());
      else if (type === "protected") layer.setStyle(protectedStyle());
      else if (type === "gir") layer.setStyle(girPointStyle(layer.feature));
      else if (type === "weather") layer.setStyle(weatherPointStyle(layer.feature));
      else if (type === "siteSelection") layer.setStyle(siteSelectionPointStyle(layer.feature));
      else layer.setStyle(suitabilityStyle(layer.feature));
    }
  });
}

async function loadGeoJson(name, path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Unable to load ${path}`);
  state.data[name] = await response.json();
}

function createLocalLayers() {
  state.localLayers.wind = L.geoJSON(state.data.wind, {
    style: suitabilityStyle,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "wind")
  });

  state.localLayers.solar = L.geoJSON(state.data.solar, {
    style: suitabilityStyle,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "solar")
  });

  state.localLayers.transmission = L.geoJSON(state.data.transmission, {
    style: transmissionStyle,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "transmission")
  });

  state.localLayers.roads = L.geoJSON(state.data.roads, {
    style: roadStyle,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "roads")
  });

  state.localLayers.protected = L.geoJSON(state.data.protected, {
    style: protectedStyle,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "protected")
  });

  state.localLayers.gir = L.geoJSON(state.data.gir, {
    pointToLayer: girPoint,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "gir")
  });

  state.localLayers.weather = L.geoJSON(state.data.weather, {
    pointToLayer: weatherPoint,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "weather")
  });

  state.localLayers.siteSelection = L.geoJSON(state.data.siteSelection, {
    pointToLayer: siteSelectionPoint,
    onEachFeature: (feature, layer) => bindCommonPopup(layer, "siteSelection")
  });

  createSiteRankLayer();
}

function createWmsLayers() {
  Object.entries(CONFIG.geoserverLayers).forEach(([name, layerName]) => {
    state.wmsLayers[name] = L.tileLayer.wms(CONFIG.geoserverWmsUrl, {
      layers: layerName,
      format: "image/png",
      transparent: true,
      version: "1.1.1",
      attribution: "GeoServer renewable_nz"
    });
  });
}

function buildHeatLayer() {
  const points = [];
  ["wind", "solar"].forEach((name) => {
    (state.data[name].features || []).forEach((feature) => {
      if (!passesSuitabilityFilter(feature.properties || {})) return;
      const center = getFeatureCenter(feature);
      if (center) points.push([center.lat, center.lng, (feature.properties.suitability_score || 0) / 100]);
    });
  });

  (state.data.gir.features || []).forEach((feature) => {
    const coords = feature.geometry.coordinates;
    points.push([coords[1], coords[0], 0.45]);
  });

  (state.data.weather.features || []).forEach((feature) => {
    const coords = feature.geometry.coordinates;
    const props = feature.properties || {};
    const windScore = Number(props.wind_resource_score || 0);
    const solarScore = Number(props.solar_resource_score || 0);
    points.push([coords[1], coords[0], Math.max(0.25, (windScore + solarScore) / 200)]);
  });

  if (state.heatLayer) map.removeLayer(state.heatLayer);
  state.heatLayer = L.heatLayer(points, {
    radius: 28,
    blur: 20,
    maxZoom: 9,
    gradient: {
      0.2: "#5a6fb0",
      0.55: "#1b7f5a",
      0.85: "#d58b18"
    }
  });

  if (state.visible.heat) state.heatLayer.addTo(map);
}

function refreshLayers() {
  const source = state.useWms ? state.wmsLayers : state.localLayers;
  const inactive = state.useWms ? state.localLayers : state.wmsLayers;

  Object.values(inactive).forEach((layer) => {
    if (map.hasLayer(layer)) map.removeLayer(layer);
  });
  if (state.rankLayer && map.hasLayer(state.rankLayer)) map.removeLayer(state.rankLayer);

  ["protected", "wind", "solar", "transmission", "roads", "gir", "weather", "siteSelection"].forEach((name) => {
    const layer = source[name];
    if (!layer) return;
    if (state.visible[name]) {
      if (!map.hasLayer(layer)) layer.addTo(map);
    } else if (map.hasLayer(layer)) {
      map.removeLayer(layer);
    }
  });

  if (state.rankLayer && state.visible.siteSelection) state.rankLayer.addTo(map);

  if (!state.useWms) {
    ["wind", "solar"].forEach((name) => state.localLayers[name].setStyle(suitabilityStyle));
  }

  buildHeatLayer();
  updateDashboard();
  updateResults();
  document.getElementById("wms-status").textContent = state.useWms ? "GeoServer WMS" : "Local data";
}

function suitabilityFeatures() {
  return ["wind", "solar"].flatMap((name) => {
    const features = state.data[name]?.features || [];
    return features.map((feature) => ({ source: name, feature }));
  });
}

function filteredSuitabilityFeatures() {
  return suitabilityFeatures().filter(({ feature }) => passesSuitabilityFilter(feature.properties || {}));
}

function updateDashboard() {
  const filtered = filteredSuitabilityFeatures();
  const top = filtered.reduce((max, item) => Math.max(max, item.feature.properties.suitability_score || 0), 0);

  document.getElementById("metric-zones").textContent = filtered.length;
  document.getElementById("metric-top").textContent = top;

  const ordered = filtered
    .slice()
    .sort((a, b) => (b.feature.properties.suitability_score || 0) - (a.feature.properties.suitability_score || 0))
    .slice(0, 6);

  const scoreData = {
    labels: ordered.map(({ feature }) => feature.properties.region_name),
    datasets: [{
      label: "Suitability score",
      data: ordered.map(({ feature }) => feature.properties.suitability_score),
      backgroundColor: ordered.map(({ feature }) => feature.properties.energy_type === "solar" ? "#d58b18" : "#5a6fb0")
    }]
  };

  const counts = filtered.reduce((acc, { feature }) => {
    const type = feature.properties.energy_type;
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, { wind: 0, solar: 0 });

  if (state.charts.score) state.charts.score.destroy();
  state.charts.score = new Chart(document.getElementById("score-chart"), {
    type: "bar",
    data: scoreData,
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxRotation: 30, minRotation: 0 } },
        y: { min: 0, max: 100 }
      }
    }
  });

  if (state.charts.energy) state.charts.energy.destroy();
  state.charts.energy = new Chart(document.getElementById("energy-chart"), {
    type: "doughnut",
    data: {
      labels: ["Wind", "Solar"],
      datasets: [{
        data: [counts.wind, counts.solar],
        backgroundColor: ["#5a6fb0", "#d58b18"],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "bottom" } }
    }
  });
}

function updateResults() {
  const container = document.getElementById("results-list");
  const filtered = filteredSuitabilityFeatures()
    .sort((a, b) => b.feature.properties.suitability_score - a.feature.properties.suitability_score);

  if (!filtered.length) {
    container.innerHTML = '<div class="result-meta">No matching suitability zones.</div>';
    return;
  }

  container.innerHTML = "";
  filtered.forEach(({ source, feature }) => {
    const props = feature.properties;
    const button = document.createElement("button");
    button.className = "result-item";
    button.innerHTML = `
      <span class="result-title">${props.region_name}</span>
      <span class="result-meta">${props.energy_type} score ${props.suitability_score} - ${props.distance_to_grid_km} km to grid</span>
    `;
    button.addEventListener("click", () => {
      const layer = findLayerForFeature(source, feature);
      if (layer) {
        map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 9 });
        layer.openPopup();
      }
    });
    container.appendChild(button);
  });
}

function findLayerForFeature(layerName, feature) {
  let found = null;
  const localLayer = state.localLayers[layerName];
  if (!localLayer) return null;
  localLayer.eachLayer((layer) => {
    if (layer.feature?.properties?.id === feature.properties.id) found = layer;
  });
  return found;
}

function searchLocations(query) {
  const q = query.trim().toLowerCase();
  if (!q) return;

  const allFeatures = [
    ...suitabilityFeatures(),
    ...(state.data.gir.features || []).map((feature) => ({ source: "gir", feature })),
    ...(state.data.weather.features || []).map((feature) => ({ source: "weather", feature })),
    ...(state.data.siteSelection.features || []).map((feature) => ({ source: "siteSelection", feature })),
    ...(state.data.roads.features || []).map((feature) => ({ source: "roads", feature }))
  ];

  const match = allFeatures.find(({ feature }) => {
    const props = feature.properties || {};
    return [props.region_name, props.place_name, props.candidate_name, props.article_title, props.energy_type, props.region, props.name, props.road_class]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(q));
  });

  if (!match) return;

  if (match.source === "gir") {
    const coords = match.feature.geometry.coordinates;
    map.setView([coords[1], coords[0]], 9);
    const layer = findPointLayer("gir", match.feature);
    if (layer) layer.openPopup();
    return;
  }

  if (match.source === "weather" || match.source === "siteSelection") {
    const coords = match.feature.geometry.coordinates;
    map.setView([coords[1], coords[0]], 9);
    const layer = findPointLayer(match.source, match.feature);
    if (layer) layer.openPopup();
    return;
  }

  const layer = findLayerForFeature(match.source, match.feature);
  if (layer) {
    map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 9 });
    layer.openPopup();
  }
}

function findPointLayer(layerName, feature) {
  let found = null;
  state.localLayers[layerName].eachLayer((layer) => {
    const layerProps = layer.feature?.properties || {};
    const featureProps = feature.properties || {};
    if (layerProps.id && layerProps.id === featureProps.id) found = layer;
    if (layerProps.rank && layerProps.rank === featureProps.rank && layerProps.energy_type === featureProps.energy_type) found = layer;
    if (layerProps.place_name && layerProps.place_name === featureProps.place_name) found = layer;
    if (layerProps.candidate_name && layerProps.candidate_name === featureProps.candidate_name) found = layer;
  });
  return found;
}

function exportVisibleGeoJson() {
  const features = [];
  ["wind", "solar", "transmission", "roads", "protected", "gir", "weather", "siteSelection"].forEach((name) => {
    if (!state.visible[name]) return;
    const data = state.data[name];
    if (data?.features) features.push(...data.features);
  });

  const blob = new Blob([JSON.stringify({ type: "FeatureCollection", features }, null, 2)], {
    type: "application/geo+json"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "visible_renewable_layers.geojson";
  link.click();
  URL.revokeObjectURL(url);
}

function attachEvents() {
  document.querySelectorAll("[data-layer]").forEach((checkbox) => {
    checkbox.addEventListener("change", (event) => {
      const name = event.target.dataset.layer;
      state.visible[name] = event.target.checked;
      refreshLayers();
    });
  });

  document.getElementById("wms-toggle").addEventListener("change", (event) => {
    state.useWms = event.target.checked;
    refreshLayers();
  });

  document.getElementById("energy-filter").addEventListener("change", (event) => {
    state.filters.energy = event.target.value;
    refreshLayers();
  });

  document.getElementById("score-filter").addEventListener("input", (event) => {
    state.filters.minScore = Number(event.target.value);
    document.getElementById("score-value").textContent = event.target.value;
    refreshLayers();
  });

  document.getElementById("search-button").addEventListener("click", () => {
    searchLocations(document.getElementById("search-input").value);
  });

  document.getElementById("search-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchLocations(event.target.value);
  });

  document.getElementById("reset-view").addEventListener("click", () => {
    map.fitBounds(CONFIG.nzBounds, { padding: [20, 20] });
  });

  document.getElementById("export-visible").addEventListener("click", exportVisibleGeoJson);
}

async function init() {
  await Promise.all(Object.entries(CONFIG.dataFiles).map(([name, path]) => loadGeoJson(name, path)));
  createLocalLayers();
  createWmsLayers();
  attachEvents();
  refreshLayers();
  map.fitBounds(CONFIG.nzBounds, { padding: [20, 20] });
}

init().catch((error) => {
  console.error(error);
  document.getElementById("results-list").innerHTML = `<div class="result-meta">${error.message}</div>`;
});
