from app import create_app, db
from app.models import DataSource

SOURCES = [
    {"name": "Smart Cities Mission Data Portal", "base_url": "https://smartcities.data.gov.in/", "access_method": "resource_download", "license_name": "Government Open Data License - India", "license_url": "https://data.gov.in/government-open-data-license-india"},
    {"name": "Open Government Data Platform India", "base_url": "https://www.data.gov.in/", "access_method": "api_or_resource", "license_name": "Government Open Data License - India", "license_url": "https://data.gov.in/government-open-data-license-india", "configuration_key": "DATA_GOV_IN_API_KEY"},
    {"name": "Central Pollution Control Board", "base_url": "https://cpcb.nic.in/", "access_method": "resource_download"},
    {"name": "OpenAQ", "base_url": "https://docs.openaq.org/", "access_method": "api", "configuration_key": "OPENAQ_API_KEY"},
    {"name": "Census of India", "base_url": "https://censusindia.gov.in/census.website/en/data", "access_method": "resource_download"},
    {"name": "OpenCity / MoRTH Road Accidents", "base_url": "https://data.opencity.in/dataset/road-accidents-in-india-2024", "access_method": "resource_download"},
    {"name": "OpenStreetMap", "base_url": "https://www.openstreetmap.in/", "access_method": "overpass_or_download", "license_name": "Open Database License (ODbL) 1.0", "license_url": "https://www.openstreetmap.org/copyright", "attribution_text": "© OpenStreetMap contributors"},
    {"name": "Central Ground Water Board", "base_url": "https://cgwb.gov.in/en/ground-water-level-monitoring", "access_method": "resource_download"},
]

app = create_app()
with app.app_context():
    for values in SOURCES:
        source = db.session.query(DataSource).filter_by(name=values["name"]).one_or_none()
        if source is None:
            db.session.add(DataSource(**values))
    db.session.commit()
    print(f"Seeded {len(SOURCES)} source records (existing records left unchanged).")
