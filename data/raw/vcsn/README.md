# VCSN Raw Data Folder

Place NIWA / Earth Sciences NZ VCSN CSV downloads here.

Accepted inputs for `scripts/vcsn_pipeline.py`:

- `.csv`
- `.txt`
- `.csv.gz`
- `.zip` containing CSV files
- a folder containing any of the above

The importer looks for these VCSN fields:

- `Station`
- `Date`
- `WindSpeed`
- `Radiation`
- `Latitude` and `Longitude`, either in the rows, in the file header metadata, or in a separate station metadata CSV.

If your VCSN download does not include coordinates in each CSV, create a metadata file using `data/raw/vcsn_station_metadata_template.csv` as the template and run:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --station-metadata data\raw\vcsn_station_metadata.csv
```

If you have DataHub API credentials, you can download all matching files from your DataHub orders:

```powershell
set NIWA_CUSTOMER_ID=your_customer_id
set NIWA_API_KEY=your_api_key

py scripts\vcsn_pipeline.py --download-all-datahub-files --datahub-name-contains vcsn --download-only
```
