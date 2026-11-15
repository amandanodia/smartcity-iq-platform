from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, func, literal, or_

from app import db
from app.models import (
    AirQuality, City, Dataset, DataSource, GeographicArea, Infrastructure,
    PopulationStatistics, RoadAccident, TrafficStatistics, WaterStatistics,
)

analytics_bp = Blueprint("analytics", __name__)

DOMAIN_CONFIG = {
    "air_quality": (AirQuality, AirQuality.pollutant, "pollutant"),
    "traffic": (TrafficStatistics, TrafficStatistics.measure, "measure"),
    "road_safety": (RoadAccident, RoadAccident.measure, "measure"),
    "water": (WaterStatistics, WaterStatistics.measure, "measure"),
    "population": (PopulationStatistics, PopulationStatistics.indicator, "indicator"),
    "infrastructure": (Infrastructure, Infrastructure.asset_type, "asset_type"),
}


def _date_param(name):
    value = request.args.get(name)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must use YYYY-MM-DD format.")


def _int_param(name):
    value = request.args.get(name)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer.")
    if parsed < 1:
        raise ValueError(f"{name} must be positive.")
    return parsed


def _analytics(domain):
    model, category_column, category_label = DOMAIN_CONFIG[domain]
    start = _date_param("start_date")
    end = _date_param("end_date")
    if domain == "population" and (start or end):
        raise ValueError("Use year_from/year_to filters for population indicators.")
    if domain != "population" and (request.args.get("year_from") or request.args.get("year_to")):
        raise ValueError("year_from/year_to filters are only supported for population indicators.")
    if start and end and start > end:
        raise ValueError("start_date must be on or before end_date.")
    city_id = _int_param("city_id")
    dataset_id = _int_param("dataset_id")
    area_id = _int_param("area_id")
    geographic_level = request.args.get("geographic_level")
    if geographic_level and geographic_level not in {"station", "ward", "city", "district", "state", "other"}:
        raise ValueError("geographic_level must be station, ward, city, district, state, or other.")
    timezone_name = request.args.get("timezone", "UTC")
    try:
        filter_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, TypeError):
        raise ValueError("timezone must be a valid IANA timezone name.")
    first_observed_at = func.min(model.observed_at).label("first_observed_at")
    last_observed_at = func.max(model.observed_at).label("last_observed_at")
    first_period_end = func.min(model.period_end).label("first_period_end") if hasattr(model, "period_end") else literal(None).label("first_period_end")
    last_period_end = func.max(model.period_end).label("last_period_end") if hasattr(model, "period_end") else literal(None).label("last_period_end")
    first_year = func.min(PopulationStatistics.reference_year).label("first_year") if domain == "population" else literal(None).label("first_year")
    last_year = func.max(PopulationStatistics.reference_year).label("last_year") if domain == "population" else literal(None).label("last_year")

    query = db.session.query(
        City.id.label("city_id"), City.name.label("city_name"), City.state_name.label("state_name"),
        GeographicArea.id.label("area_id"), GeographicArea.name.label("area_name"),
        GeographicArea.area_type.label("geographic_level"),
        Dataset.id.label("dataset_id"), Dataset.name.label("dataset_name"),
        Dataset.record_class.label("record_class"), Dataset.source_url.label("source_url"),
        DataSource.name.label("source_name"), DataSource.attribution_text.label("attribution_text"),
        DataSource.license_name.label("license_name"), category_column.label("category"),
        model.normalized_unit.label("unit"), func.count(model.id).label("observation_count"),
        func.avg(model.normalized_value).label("mean_value"), func.max(model.normalized_value).label("max_value"),
        func.min(model.normalized_value).label("min_value"), first_observed_at, last_observed_at,
        first_period_end, last_period_end, first_year, last_year,
    ).join(Dataset, Dataset.id == model.dataset_id).join(DataSource, DataSource.id == Dataset.data_source_id)
    query = query.outerjoin(City, City.id == model.city_id).outerjoin(GeographicArea, GeographicArea.id == model.geographic_area_id)
    query = query.filter(model.normalized_value.is_not(None))
    if city_id:
        query = query.filter(model.city_id == city_id)
    if dataset_id:
        query = query.filter(model.dataset_id == dataset_id)
    if area_id:
        query = query.filter(model.geographic_area_id == area_id)
    if geographic_level:
        if geographic_level == "city":
            query = query.filter(or_(GeographicArea.id.is_(None), GeographicArea.area_type == "city"))
        else:
            query = query.filter(GeographicArea.area_type == geographic_level)
    category_filter = request.args.get(category_label)
    if category_filter:
        query = query.filter(category_column == category_filter)
    normalized_unit = request.args.get("unit")
    if normalized_unit:
        query = query.filter(model.normalized_unit == normalized_unit)

    if domain == "population":
        try:
            year_from = int(request.args["year_from"]) if request.args.get("year_from") else None
            year_to = int(request.args["year_to"]) if request.args.get("year_to") else None
        except ValueError:
            raise ValueError("year_from and year_to must be integers.")
        if (year_from is not None and year_from < 1800) or (year_to is not None and year_to > 2200):
            raise ValueError("Population year filters must be between 1800 and 2200.")
        if (year_from is not None and year_from > 2200) or (year_to is not None and year_to < 1800):
            raise ValueError("Population year filters must be between 1800 and 2200.")
        if year_from:
            query = query.filter(PopulationStatistics.reference_year >= year_from)
        if year_to:
            query = query.filter(PopulationStatistics.reference_year <= year_to)
        if year_from and year_to and year_from > year_to:
            raise ValueError("year_from must be on or before year_to.")
    else:
        if start:
            start_dt = datetime.combine(start, time.min, tzinfo=filter_timezone)
            if hasattr(model, "period_end"):
                query = query.filter(or_(model.observed_at >= start_dt, and_(model.observed_at.is_(None), model.period_end >= start)))
            else:
                query = query.filter(model.observed_at >= start_dt)
        if end:
            end_exclusive = end + timedelta(days=1)
            end_dt = datetime.combine(end_exclusive, time.min, tzinfo=filter_timezone)
            if hasattr(model, "period_end"):
                query = query.filter(or_(model.observed_at < end_dt, and_(model.observed_at.is_(None), model.period_end <= end)))
            else:
                query = query.filter(model.observed_at < end_dt)

    groups = [City.id, City.name, City.state_name, GeographicArea.id, GeographicArea.name,
              GeographicArea.area_type, Dataset.id, Dataset.name, Dataset.record_class,
              Dataset.source_url, DataSource.name, DataSource.attribution_text, DataSource.license_name,
              category_column, model.normalized_unit]
    rows = query.group_by(*groups).order_by(City.name, Dataset.name, category_column).limit(1000).all()
    data = []
    for row in rows:
        start_value = row.first_observed_at or row.first_period_end or row.first_year
        end_value = row.last_observed_at or row.last_period_end or row.last_year
        coverage = {
            "city": row.city_name,
            "state": row.state_name,
            "geographic_level": row.geographic_level or ("city" if row.city_name else "unknown"),
            "area": row.area_name,
        }
        data.append({
            "city_id": row.city_id, "city": row.city_name, "category": row.category,
            "category_type": category_label, "unit": row.unit,
            "observation_count": row.observation_count,
            "mean": float(row.mean_value) if row.mean_value is not None else None,
            "maximum_recorded": float(row.max_value) if row.max_value is not None else None,
            "minimum_recorded": float(row.min_value) if row.min_value is not None else None,
            "reporting_period": {"start": start_value.isoformat() if hasattr(start_value, "isoformat") else str(start_value) if start_value is not None else None,
                                 "end": end_value.isoformat() if hasattr(end_value, "isoformat") else str(end_value) if end_value is not None else None},
            "coverage": coverage,
            "dataset": {"id": row.dataset_id, "name": row.dataset_name, "record_class": row.record_class,
                        "source": row.source_name, "source_url": row.source_url,
                        "attribution": row.attribution_text, "license": row.license_name},
        })
    warnings = []
    if len(rows) == 1000:
        warnings.append("Result groups were capped at 1000; add filters to narrow the request.")
    if any(item["unit"] is None for item in data):
        warnings.append("Some measurements have no declared unit; those groups are not comparable by unit.")
    if any(item["city_id"] is None for item in data):
        warnings.append("Some records are not assigned to a city and appear with unknown city coverage.")
    comparable_series = bool(dataset_id and category_filter and normalized_unit and geographic_level and len(rows) < 1000)
    insights = []
    if comparable_series and data:
        by_city = {}
        for item in data:
            city_key = item["city_id"]
            if city_key is None:
                continue
            group = by_city.setdefault(city_key, {"city_id": city_key, "city": item["city"],
                "maximum_recorded": item["maximum_recorded"], "unit": item["unit"],
                "observation_count": 0, "period_start": None, "period_end": None,
                "source": item["dataset"], "coverage_areas": set()})
            group["observation_count"] += item["observation_count"]
            if item["maximum_recorded"] is not None:
                group["maximum_recorded"] = max(group["maximum_recorded"], item["maximum_recorded"])
            if item["reporting_period"]["start"]:
                group["period_start"] = min(filter(None, [group["period_start"], item["reporting_period"]["start"]]))
            if item["reporting_period"]["end"]:
                group["period_end"] = max(filter(None, [group["period_end"], item["reporting_period"]["end"]]))
            if item["coverage"]["area"]:
                group["coverage_areas"].add(item["coverage"]["area"])
        by_maximum = sorted(by_city.values(), key=lambda item: item["maximum_recorded"], reverse=True)
        if by_maximum:
            winning_value = by_maximum[0]["maximum_recorded"]
            winners = [item for item in by_maximum if item["maximum_recorded"] == winning_value]
            insights.append({"name": "highest_recorded_value_by_city", "method": "Maximum normalized value per city across the selected dataset, category, unit, period, and geographic level.",
                             "winners": [{"city_id": item["city_id"], "city": item["city"],
                                          "maximum_recorded": item["maximum_recorded"], "unit": item["unit"],
                                          "observation_count": item["observation_count"], "source": item["source"],
                                          "coverage": {"geographic_level": geographic_level,
                                                       "areas": sorted(item["coverage_areas"])},
                                          "reporting_period": {"start": item["period_start"], "end": item["period_end"]}}
                                         for item in winners]})
    insight_note = None if insights else "For a comparable highest-recorded city result, select one dataset, category, unit, and geographic_level."
    return {"domain": domain, "calculation": "mean/minimum/maximum of normalized_value within each dataset, city/area, category, and unit group; null values excluded.",
            "filters": {"city_id": city_id, "dataset_id": dataset_id, "area_id": area_id, "start_date": start.isoformat() if start else None,
                        "end_date": end.isoformat() if end else None, "geographic_level": geographic_level,
                        "timezone": timezone_name,
                        "year_from": request.args.get("year_from") if domain == "population" else None,
                        "year_to": request.args.get("year_to") if domain == "population" else None,
                        "category": category_filter, "unit": normalized_unit},
            "data": data, "insights": insights, "meta": {"group_count": len(data), "warnings": warnings, "insight_note": insight_note,
                                     "message": None if data else "No normalized measurements are available for these filters."}}


@analytics_bp.get("/analytics/<string:domain>")
def analytics_domain(domain):
    domain = domain.replace("-", "_")
    if domain not in DOMAIN_CONFIG:
        return jsonify({"error": {"code": "unknown_domain", "message": "Supported domains: air_quality, traffic, road_safety, water, population, infrastructure."}}), 404
    try:
        return jsonify(_analytics(domain))
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_filter", "message": str(exc)}}), 400


@analytics_bp.get("/analytics/city-comparison")
def city_comparison():
    domain = request.args.get("domain", "").replace("-", "_")
    if domain not in DOMAIN_CONFIG:
        return jsonify({"error": {"code": "domain_required", "message": "Select a supported domain query parameter."}}), 400
    try:
        return jsonify(_analytics(domain))
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_filter", "message": str(exc)}}), 400
