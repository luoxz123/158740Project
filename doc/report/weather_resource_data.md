# Historical Weather Resource Data

This project should not use normal website scraping for historical wind and sunshine data. Weather history is structured time-series data and should come from climate databases or weather APIs.

This is the physical resource collection method. It is separate from the web text GIR workflow in `scripts/gir_pipeline.py`.

## Recommended Sources

### Open-Meteo Historical Weather API

Open-Meteo provides historical weather data from reanalysis datasets. It includes hourly variables useful for renewable energy planning:

- `wind_speed_10m`
- `wind_speed_100m`
- `wind_gusts_10m`
- `shortwave_radiation`
- `sunshine_duration`

The project script `scripts/weather_history_pipeline.py` uses this source because it is easy to run in a student project and does not require an API key. The default input file is `data/raw/weather_locations_extended.csv`, which contains rural, coastal, and inland analysis points that are more relevant to wind farm and solar farm siting than city-only weather points.

### NIWA / Earth Sciences New Zealand CliFlo

CliFlo is the official New Zealand national climate database. It is better for station-observed weather data, but normally requires account-based data download and has row limits. It is appropriate to cite as an official source or use for manually downloaded station data.

### NIWA Virtual Climate Station Network

NIWA DataHub provides Virtual Climate Station Network data on a regular approximately 5 km grid covering New Zealand. This is the strongest public-source direction for rural renewable resource modelling because it is not limited to city stations. It includes variables such as solar radiation and wind speed.

The project importer is `scripts/vcsn_pipeline.py`. It expects VCSN CSV fields such as `Station`, `Date`, `WindSpeed`, and `Radiation`. `WindSpeed` is daily mean wind speed at 10 m above ground level in m/s. `Radiation` is daily accumulated global solar radiation in MJ/m2. The script converts radiation to kWh/m2 and estimates 100 m wind speed from 10 m wind speed using a power-law wind shear factor for wind farm comparison.

### MetService

MetService forecast and warning web pages are useful for current severe weather context, but they are not a practical source for bulk historical wind and sunshine data through simple HTML scraping. Use MetService API/Data Hub only if access is available. The public MetService observation API requires access approval and its documented history horizon is short compared with a full-year suitability analysis. MetService states that observational data collected for public forecast services is passed to Earth Sciences NZ for archiving in the National Climate Database.

### Weather Underground

Weather Underground can display historical observations for personal and official stations, but it is not recommended as the primary source for this project. The data quality varies by personal weather station, the site is dynamic, bulk scraping is fragile, and there is no simple open bulk API suitable for an assessed WebGIS data pipeline. If Weather Underground data is used, export station records manually or through approved access, then import them as a CSV-derived supplementary layer.

## Source Notes

- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- MetService 1-Minute Observations API: https://developer.metservice.com/docs/api-catalog/1min-obs-api/
- NIWA DataHub climate collection: https://data.niwa.co.nz/collections/climate
- NIWA VCSN timeseries: https://data.niwa.co.nz/products/vcsn-timeseries
- Earth Sciences NZ / NIWA CliFlo help: https://niwa.co.nz/climate-and-weather/help-using-national-climate-database-cliflo
- MetService roles and observational data distribution: https://about.metservice.com/about-us/roles-and-responsibilities
- Weather Underground data notes: https://www.wunderground.com/about/data

## Run The Weather Pipeline

Install dependencies:

```powershell
py -m pip install requests psycopg2-binary
```

Download the last year of hourly weather resource data:

```powershell
py scripts\weather_history_pipeline.py
```

Run a quick 5-point test:

```powershell
py scripts\weather_history_pipeline.py --max-locations 5
```

Use the smaller original city sample:

```powershell
py scripts\weather_history_pipeline.py --city-sample
```

Download a fixed analysis period and insert into PostGIS:

```powershell
py scripts\weather_history_pipeline.py --start-date 2024-01-01 --end-date 2024-12-31 --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

## Run The VCSN Pipeline

Download VCSN CSV files from NIWA / Earth Sciences NZ DataHub into:

```text
data/raw/vcsn/
```

Then run:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --summary-output data\processed\vcsn_weather_resource_summary.csv --geojson-output frontend\data\weather_resource_summary.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

If the VCSN CSV files do not include coordinates in each row, provide station metadata:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --station-metadata data\raw\vcsn_station_metadata.csv --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

If the files are already in your DataHub orders, use the DataHub API to download them in bulk:

```powershell
set NIWA_CUSTOMER_ID=your_customer_id
set NIWA_API_KEY=your_api_key

py scripts\vcsn_pipeline.py --download-all-datahub-files --datahub-name-contains vcsn --download-only
```

After the download, import the local files:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

The VCSN output uses the same frontend weather resource layer, so the map will show all imported VCSN points instead of the smaller 87-point Open-Meteo sample.

Outputs:

- `data/processed/weather_hourly_history.csv`
- `data/processed/weather_resource_summary.csv`
- `frontend/data/weather_resource_summary.geojson`
- PostGIS table `renewable_nz.weather_resource_summary` when `--insert-db` is used

## How To Use In Suitability Analysis

For wind farm suitability:

- Prefer `mean_wind_speed_100m_ms`.
- Use `p90_wind_speed_100m_ms` to identify consistently windy locations.
- Use `max_wind_gust_10m_ms` as a risk or operational constraint.

For solar farm suitability:

- Use `total_shortwave_radiation_kwh_m2`.
- Use `total_sunshine_hours`.
- Compare with slope, protected areas, and grid distance.
