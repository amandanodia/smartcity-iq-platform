# Provider connectors

Connector methods fetch provider-shaped payloads. They do not normalize measurements or write domain observations. Persist connector results through the ingestion workflow and retain the source resource URL and provider attribution.

| Connector | Access currently implemented | Configuration |
|---|---|---|
| data.gov.in | Resource API JSON | `DATA_GOV_IN_API_KEY` plus a verified resource ID |
| OpenAQ | API v3 JSON | `OPENAQ_API_KEY`; endpoints are relative to `/v3/` |
| Smart Cities portal | Registered resource CSV/Excel/JSON download | Verified HTTPS resource URL in dataset connector configuration |
| CPCB | Registered resource file download | Verified CPCB/CPCB CCR resource URL; no endpoint is invented |
| Census of India | Registered resource file download | Verified official download URL; otherwise use manual import |
| OpenCity / MoRTH | Registered resource file download | Verified OpenCity resource URL |
| OpenStreetMap | Overpass JSON | Explicit Overpass query and approved endpoint; follow usage policy and attribute ODbL data |
| CGWB | Registered resource file download | Verified CGWB/India-WRIS downloadable URL; no assumption of a public API |

File URL fetches require HTTPS and allowlisted provider hosts. Provider responses are size-limited and time-limited. Unavailable credentials or unconfigured resource IDs produce configuration errors instead of fabricated empty results.

OpenAQ API v3 requires an `X-API-Key` header and applies key-scoped request limits; configure `OPENAQ_API_KEY` in the environment. See [OpenAQ key documentation](https://docs.openaq.org/using-the-api/api-key) and [rate-limit guidance](https://docs.openaq.org/using-the-api/rate-limits). `data.gov.in` resources vary by dataset; verify the dataset's API/resource ID and access terms before configuring a connector.
