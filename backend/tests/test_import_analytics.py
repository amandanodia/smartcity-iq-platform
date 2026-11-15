import io

from app import db
from app.models import AirQuality, ImportBatch


def test_import_normalization_and_analytics_preserve_quality(client, app):
    csv_bytes = (
        "Record ID,Date,City,PM2.5,Unit\n"
        "r1,2024-01-01T10:00:00Z,Delhi,42,ug/m3\n"
        "r2,2024-01-01T11:00:00Z,Delhi,,ug/m3\n"
        "r3,2024-01-01T12:00:00Z,Delhi,44,ug/m3\n"
        "r3,2024-01-01T12:00:00Z,Delhi,44,ug/m3\n"
    ).encode()
    response = client.post("/api/import/csv", data={
        "dataset_id": str(app.config["TEST_DATASET_ID"]),
        "file": (io.BytesIO(csv_bytes), "air.csv", "text/csv"),
    }, content_type="multipart/form-data")
    assert response.status_code == 201
    batch_id = response.get_json()["data"]["import_batch_id"]

    processed = client.post(f"/api/import-batches/{batch_id}/process", json={"mapping": {
        "value_column": "PM2.5", "date_column": "Date", "city_column": "City",
        "pollutant": "PM2.5", "unit_column": "Unit", "source_record_id_column": "Record ID",
    }})
    assert processed.status_code == 200
    payload = processed.get_json()["data"]
    assert payload["rows_inserted"] == 2
    assert payload["rows_rejected"] == 2
    assert payload["duplicate_exact_rows"] == 1
    assert payload["missing_values_rejected"] == 1

    with app.app_context():
        observations = AirQuality.query.all()
        assert len(observations) == 2
        assert all(row.original_value == row.normalized_value for row in observations)
        assert all(row.original_unit == row.normalized_unit == "ug/m3" for row in observations)
        batch = db.session.get(ImportBatch, batch_id)
        assert batch.status == "processed_with_warnings"
        assert batch.rows_rejected == 2

    analytics = client.get(f"/api/analytics/air-quality?dataset_id={app.config['TEST_DATASET_ID']}&pollutant=PM2.5&unit=ug%2Fm3&geographic_level=city")
    assert analytics.status_code == 200
    results = analytics.get_json()["data"]
    assert len(results) == 1
    assert results[0]["observation_count"] == 2
    assert results[0]["mean"] == 43
    assert results[0]["maximum_recorded"] == 44
    assert results[0]["dataset"]["record_class"] == "manually_imported"


def test_analytics_empty_state_does_not_return_zero_measurement(client):
    response = client.get("/api/analytics/air-quality")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"] == []
    assert payload["meta"]["message"] == "No normalized measurements are available for these filters."


def test_monitoring_station_route_returns_unavailable_when_no_coordinates(client, app):
    response = client.get(f"/api/monitoring-stations?city_id={app.config['TEST_CITY_ID']}")
    assert response.status_code == 200
    assert response.get_json()["data"] == []
    assert "No monitoring stations" in response.get_json()["meta"]["message"]
