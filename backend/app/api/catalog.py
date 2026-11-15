from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app.models import City, DataQualityReport, DataSource, Dataset, DatasetCoverage, GeographicArea, MonitoringStation

catalog_bp = Blueprint("catalog", __name__)


def _positive_int(value, default, maximum):
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("pagination values must be integers.")
    if parsed < 1:
        raise ValueError("pagination values must be positive.")
    return min(parsed, maximum)


@catalog_bp.get("/cities")
def list_cities():
    cities = City.query.filter_by(is_active=True).order_by(City.name).all()
    return jsonify({"data": [{"id": c.id, "name": c.name, "state": c.state_name, "slug": c.slug} for c in cities], "meta": {"count": len(cities)}})


@catalog_bp.get("/cities/<int:city_id>")
def get_city(city_id):
    city = City.query.filter_by(id=city_id, is_active=True).one_or_none()
    if city is None:
        return jsonify({"error": {"code": "not_found", "message": "City not found."}}), 404
    return jsonify({"data": {"id": city.id, "name": city.name, "state": city.state_name, "slug": city.slug, "country_code": city.country_code}})


@catalog_bp.get("/datasets")
def list_datasets():
    try:
        page = _positive_int(request.args.get("page"), 1, 1000000)
        per_page = _positive_int(request.args.get("per_page"), 50, 100)
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_pagination", "message": str(exc)}}), 400
    query = Dataset.query
    if request.args.get("domain"):
        query = query.filter_by(domain=request.args["domain"])
    if request.args.get("city_id"):
        try:
            city_id = int(request.args["city_id"])
            if city_id < 1:
                raise ValueError
        except ValueError:
            return jsonify({"error": {"code": "invalid_city_id", "message": "city_id must be a positive integer."}}), 400
        query = query.join(DatasetCoverage).filter(DatasetCoverage.city_id == city_id).distinct()
    pagination = query.order_by(Dataset.name).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "data": [{"id": d.id, "name": d.name, "domain": d.domain, "source_id": d.data_source_id,
                  "source_url": d.source_url, "record_class": d.record_class} for d in pagination.items],
        "meta": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    })


@catalog_bp.get("/datasets/coverage")
def list_coverage():
    query = DatasetCoverage.query
    city_id = request.args.get("city_id")
    if city_id:
        try:
            parsed_id = int(city_id)
            if parsed_id < 1:
                raise ValueError
            query = query.filter_by(city_id=parsed_id)
        except ValueError:
            return jsonify({"error": {"code": "invalid_city_id", "message": "city_id must be a positive integer."}}), 400
    rows = query.order_by(DatasetCoverage.dataset_id, DatasetCoverage.city_id).limit(500).all()
    return jsonify({"data": [{"dataset_id": r.dataset_id, "city_id": r.city_id, "area_id": r.geographic_area_id,
                              "geographic_level": r.geographic_level, "period_start": r.period_start.isoformat() if r.period_start else None,
                              "period_end": r.period_end.isoformat() if r.period_end else None, "status": r.coverage_status,
                              "notes": r.notes} for r in rows], "meta": {"count": len(rows), "limit": 500}})


@catalog_bp.get("/data-sources")
def list_sources():
    sources = DataSource.query.order_by(DataSource.name).all()
    return jsonify({"data": [{"id": s.id, "name": s.name, "base_url": s.base_url, "access_method": s.access_method,
                              "license": s.license_name, "license_url": s.license_url,
                              "attribution": s.attribution_text} for s in sources], "meta": {"count": len(sources)}})


@catalog_bp.get("/monitoring-stations")
def list_monitoring_stations():
    query = MonitoringStation.query.join(Dataset, Dataset.id == MonitoringStation.dataset_id).outerjoin(
        City, City.id == MonitoringStation.city_id
    ).options(joinedload(MonitoringStation.dataset), joinedload(MonitoringStation.city)).filter(
        MonitoringStation.latitude.is_not(None), MonitoringStation.longitude.is_not(None)
    )
    city_id = request.args.get("city_id")
    dataset_id = request.args.get("dataset_id")
    area_id = request.args.get("area_id")
    try:
        if city_id:
            parsed_city_id = int(city_id)
            if parsed_city_id < 1:
                raise ValueError
            query = query.filter(MonitoringStation.city_id == parsed_city_id)
        if dataset_id:
            parsed_dataset_id = int(dataset_id)
            if parsed_dataset_id < 1:
                raise ValueError
            query = query.filter(MonitoringStation.dataset_id == parsed_dataset_id)
        if area_id:
            parsed_area_id = int(area_id)
            if parsed_area_id < 1:
                raise ValueError
            query = query.filter(MonitoringStation.geographic_area_id == parsed_area_id)
    except ValueError:
        return jsonify({"error": {"code": "invalid_filter", "message": "city_id, dataset_id, and area_id must be positive integers."}}), 400
    stations = query.order_by(City.name, MonitoringStation.name).limit(500).all()
    data = []
    for station in stations:
        if not (-90 <= station.latitude <= 90 and -180 <= station.longitude <= 180):
            continue
        data.append({"id": station.id, "name": station.name, "latitude": station.latitude,
                     "longitude": station.longitude, "active": station.is_active,
                     "city_id": station.city_id, "city": station.city.name if station.city else None,
                     "state": station.city.state_name if station.city else None,
                     "dataset_id": station.dataset_id, "dataset": station.dataset.name,
                     "record_class": station.dataset.record_class, "source_url": station.dataset.source_url})
    return jsonify({"data": data, "meta": {"count": len(data), "limit": 500,
                                               "capped": len(stations) == 500,
                                               "message": None if data else "No monitoring stations with valid coordinates are available for these filters."}})


@catalog_bp.get("/geographic-areas")
def list_geographic_areas():
    query = GeographicArea.query.outerjoin(City, City.id == GeographicArea.city_id).options(
        joinedload(GeographicArea.city)
    )
    city_id = request.args.get("city_id")
    area_type = request.args.get("area_type")
    try:
        if city_id:
            parsed_city_id = int(city_id)
            if parsed_city_id < 1:
                raise ValueError
            query = query.filter(GeographicArea.city_id == parsed_city_id)
    except ValueError:
        return jsonify({"error": {"code": "invalid_city_id", "message": "city_id must be a positive integer."}}), 400
    valid_types = {"station", "ward", "city", "district", "state", "other"}
    if area_type:
        if area_type not in valid_types:
            return jsonify({"error": {"code": "invalid_area_type", "message": "Unknown geographic area type."}}), 400
        query = query.filter(GeographicArea.area_type == area_type)
    areas = query.order_by(City.name, GeographicArea.name).limit(1000).all()
    return jsonify({"data": [{"id": area.id, "city_id": area.city_id, "city": area.city.name if area.city else None,
                              "state": area.city.state_name if area.city else None, "name": area.name,
                              "area_type": area.area_type, "parent_id": area.parent_id}
                             for area in areas],
                    "meta": {"count": len(areas), "limit": 1000, "capped": len(areas) == 1000}})


@catalog_bp.get("/data-quality")
def list_quality_reports():
    try:
        page = _positive_int(request.args.get("page"), 1, 1000000)
        per_page = _positive_int(request.args.get("per_page"), 50, 100)
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_pagination", "message": str(exc)}}), 400
    pagination = DataQualityReport.query.order_by(DataQualityReport.generated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"data": [{"id": r.id, "dataset_id": r.dataset_id, "import_batch_id": r.import_batch_id,
                              "generated_at": r.generated_at.isoformat(), "rows_checked": r.rows_checked,
                              "duplicate_rows": r.duplicate_rows, "missing_value_counts": r.missing_value_counts,
                              "warnings": r.warnings} for r in pagination.items],
                    "meta": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages}})
