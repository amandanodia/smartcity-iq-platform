from app import create_app, db
from app.models import City

CITIES = [
    ("Jaipur", "Rajasthan", "jaipur-rajasthan"),
    ("Delhi", "Delhi", "delhi"),
    ("Mumbai", "Maharashtra", "mumbai-maharashtra"),
    ("Bengaluru", "Karnataka", "bengaluru-karnataka"),
    ("Hyderabad", "Telangana", "hyderabad-telangana"),
    ("Chennai", "Tamil Nadu", "chennai-tamil-nadu"),
    ("Pune", "Maharashtra", "pune-maharashtra"),
    ("Ahmedabad", "Gujarat", "ahmedabad-gujarat"),
]

app = create_app()
with app.app_context():
    for name, state, slug in CITIES:
        city = db.session.query(City).filter_by(slug=slug).one_or_none()
        if city is None:
            db.session.add(City(name=name, state_name=state, slug=slug))
    db.session.commit()
    print(f"Seeded {len(CITIES)} city records (existing slugs left unchanged).")
