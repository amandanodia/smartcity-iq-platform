# Data sources

Phase 1 source investigation and its city-level availability matrix are recorded in the project approval conversation. Availability is not guaranteed merely because a portal or catalog exists. Verify resource records, temporal range, geography, licensing, and access limits before ingestion.

Candidate official/primary source links:

- Smart Cities Mission Data Portal: https://smartcities.data.gov.in/
- Open Government Data Platform: https://www.data.gov.in/
- CPCB: https://cpcb.nic.in/
- OpenAQ API docs: https://docs.openaq.org/
- Census of India data: https://censusindia.gov.in/census.website/en/data
- MoRTH road accident resources via OpenCity: https://data.opencity.in/dataset/road-accidents-in-india-2024
- OpenStreetMap India: https://www.openstreetmap.in/
- CGWB groundwater monitoring: https://cgwb.gov.in/en/ground-water-level-monitoring

Each imported dataset must retain its original source URL, license/attribution details, observation date, import date, geographic coverage, and source units. Missing values remain missing; they are never converted to zero implicitly.
