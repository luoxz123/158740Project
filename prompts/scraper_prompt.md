# Renewable Energy GIR Scraper Prompt

Build a Python pipeline that:

1. Scrapes renewable energy news articles
2. Extracts geographic place names using SpaCy NER
3. Geocodes locations using GeoPy
4. Generates GeoJSON output

Requirements:

- Use requests
- Use BeautifulSoup
- Use SpaCy
- Use GeoPy
- Export valid GeoJSON

Target keywords:

- wind farm
- solar farm
- renewable energy

Output fields:

- article_title
- place_name
- latitude
- longitude
- energy_type
- source_url

Save output as:

renewable_energy_mentions.geojson