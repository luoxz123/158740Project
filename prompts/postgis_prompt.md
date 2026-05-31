# PostGIS Prompt

Generate PostgreSQL/PostGIS SQL scripts for a renewable energy suitability system.

Requirements:

Create tables for:

- solar suitability
- wind suitability
- transmission lines
- roads
- protected areas
- GIR extracted locations

Requirements:

- Use EPSG:2193
- Create spatial indexes
- Include geometry validation
- Use PostGIS best practices

Generate:

- schema.sql
- indexes.sql
- sample spatial queries