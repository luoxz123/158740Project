# Wind And Solar Site Selection Analysis

This project does not use paid NIWA VCSN downloads. Instead, it ranks candidate sites using the already collected 87-point weather resource dataset.

## Inputs

- `data/processed/weather_resource_summary.csv`
- `frontend/data/transmission_lines.geojson`
- `data/processed/renewable_energy_mentions.geojson`

## Method

1. Generate candidate locations from the 87 weather resource points.
2. Add interpolated midpoint candidates between nearby weather points.
3. Estimate wind and solar resource values at each candidate using inverse distance weighting.
4. Calculate distance from each candidate to the nearest transmission line.
5. Score nearby GIR news and weather evidence from renewable-energy mentions.
6. Rank wind and solar candidates separately.

## Score Formula

Final score:

```text
55% weather resource score
25% transmission proximity score
15% GIR evidence score
5% interpolation confidence
```

## Run

```powershell
py scripts\site_selection_analysis.py
```

Insert the top 10 wind and top 10 solar candidates into PostGIS:

```powershell
py scripts\site_selection_analysis.py --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

## Outputs

- `data/processed/wind_farm_candidates_top10.csv`
- `data/processed/solar_farm_candidates_top10.csv`
- `data/processed/site_selection_top10.csv`
- `frontend/data/site_selection_candidates.geojson`

The frontend displays the output as the `Recommended sites` layer.

## Limitations

This is a planning-level screening model. It does not replace engineering design, land ownership checks, consenting review, terrain modelling, ecological constraints, or high-resolution grid connection studies.
