# Data Dictionary

## wind_suitability

| Field | Description |
|---|---|
| `region_name` | Candidate wind zone name |
| `suitability_score` | Normalised suitability score from 0 to 100 |
| `avg_wind_speed` | Indicative average wind speed |
| `distance_to_grid_km` | Distance to transmission grid |
| `slope_degree` | Indicative terrain slope |
| `constraint_level` | Planning constraint category |

## solar_suitability

| Field | Description |
|---|---|
| `region_name` | Candidate solar zone name |
| `suitability_score` | Normalised suitability score from 0 to 100 |
| `solar_irradiance_kwh_m2` | Indicative solar irradiance |
| `distance_to_grid_km` | Distance to transmission grid |
| `slope_degree` | Indicative terrain slope |
| `constraint_level` | Planning constraint category |

## gir_locations

| Field | Description |
|---|---|
| `article_title` | Source article title |
| `place_name` | Extracted place name |
| `latitude` | WGS84 latitude |
| `longitude` | WGS84 longitude |
| `energy_type` | Wind, solar, mixed, or renewable |
| `source_url` | Source article URL |
| `confidence` | Simple confidence score for geocoding/source quality |

## weather_resource_summary

| Field | Description |
|---|---|
| `place_name` | Weather resource analysis point name |
| `region` | New Zealand region |
| `mean_wind_speed_100m_ms` | Mean wind speed estimated at 100 m in m/s |
| `p90_wind_speed_100m_ms` | 90th percentile 100 m wind speed in m/s |
| `total_shortwave_radiation_kwh_m2` | Annual shortwave solar radiation in kWh/m2 |
| `total_sunshine_hours` | Annual sunshine duration in hours |
| `wind_resource_score` | Normalised wind resource score from 0 to 100 |
| `solar_resource_score` | Normalised solar resource score from 0 to 100 |

## site_selection_candidates

| Field | Description |
|---|---|
| `rank` | Rank within the wind or solar candidate list |
| `energy_type` | Candidate type, wind or solar |
| `candidate_name` | Recommended site or corridor name |
| `final_score` | Weighted candidate score |
| `weather_resource_score` | IDW-interpolated weather resource score |
| `grid_connection_score` | Score based on proximity to transmission lines |
| `gir_evidence_score` | Score based on nearby GIR news/weather evidence |
| `interpolation_confidence` | Confidence based on distance to nearest measured weather point |
| `distance_to_transmission_km` | Distance to nearest transmission line |
