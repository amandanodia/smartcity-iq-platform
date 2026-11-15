import pytest
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from app import create_app, db
from app.models import City, DataSource, Dataset


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(_type, _compiler, **_kw):
    return "INTEGER"


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "IMPORT_STORAGE_DIR": str(tmp_path / "uploads"),
        "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
    })
    with application.app_context():
        db.create_all()
        source = DataSource(name="Test source", base_url="https://example.gov", access_method="manual")
        db.session.add(source)
        db.session.flush()
        city = City(name="Delhi", state_name="Delhi", slug="delhi")
        db.session.add(city)
        db.session.flush()
        dataset = Dataset(data_source_id=source.id, name="Test air observations", domain="air_quality",
                          source_dataset_id="test-air", source_url="https://example.gov/air.csv", record_class="historical")
        db.session.add(dataset)
        db.session.commit()
        application.config["TEST_CITY_ID"] = city.id
        application.config["TEST_DATASET_ID"] = dataset.id
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
