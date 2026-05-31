# GIR Live Collection Workflow

## What The Script Can Do

`scripts/gir_pipeline.py` can now:

- Discover candidate RNZ, Stuff, and NZ Herald pages from public sitemap files.
- Filter articles using renewable-energy keywords.
- Extract New Zealand place names using spaCy plus a local place-name gazetteer.
- Geocode places with GeoPy/Nominatim or local cached coordinates.
- Export GeoJSON.
- Insert extracted point features directly into PostGIS table `renewable_nz.gir_locations`.

This is the web text collection method. It is separate from `scripts/weather_history_pipeline.py`, which collects structured historical weather variables.

## Recommended VM Commands

Install dependencies:

```powershell
py -m pip install -r requirements.txt
py -m spacy download en_core_web_sm
```

Run conservative automatic discovery:

```powershell
py scripts\gir_pipeline.py --auto-discover --max-pages-per-site 80 --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

Run deeper scanning, with more pages per site:

```powershell
py scripts\gir_pipeline.py --auto-discover --deep-scan --max-pages-per-site 300 --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

Use known local coordinates only, without live geocoding:

```powershell
py scripts\gir_pipeline.py --auto-discover --offline-geocode --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

If you want current MetService warning text as GIR evidence, pass it explicitly as a site:

```powershell
py scripts\gir_pipeline.py --auto-discover --deep-scan --offline-geocode --sites https://www.metservice.com/ --frontend-output frontend\data\gir_mentions.geojson
```

Do not use this MetService page scan for historical wind speed or sunshine hours. Use the weather resource pipeline for that.

## Facebook Handling

Do not use blind Facebook scraping for the assessed project. Use one of these safer methods:

- Export text manually into `data/raw/facebook_mentions.csv`.
- Use approved Meta tools/API access if your account and project have permission.

Then run:

```powershell
py scripts\gir_pipeline.py --include-facebook-csv --offline-geocode --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

The CSV format is:

```csv
title,source_url,text
"Facebook sample renewable discussion","facebook://manual-sample","Solar energy projects in Canterbury and wind farms in Taranaki."
```
