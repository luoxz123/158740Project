# GIR Pipeline Prompt

Build a Python Geographic Information Retrieval pipeline.

The pipeline must:

- Read renewable energy article URLs or local sample article text
- Scrape article title and body text
- Extract place names using SpaCy NER
- Geocode places using GeoPy
- Infer energy type from article text
- Export valid GeoJSON point features
- Support offline sample mode for testing
