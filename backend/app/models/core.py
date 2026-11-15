from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class City(TimestampMixin, db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    state_name = db.Column(db.String(120), nullable=False)
    country_code = db.Column(db.String(2), nullable=False, default="IN")
    slug = db.Column(db.String(140), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (UniqueConstraint("name", "state_name", name="uq_cities_name_state"),)


class DataSource(TimestampMixin, db.Model):
    __tablename__ = "data_sources"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    base_url = db.Column(db.Text)
    access_method = db.Column(db.String(40), nullable=False, default="manual")
    license_name = db.Column(db.String(200))
    license_url = db.Column(db.Text)
    attribution_text = db.Column(db.Text)
    configuration_key = db.Column(db.String(160))
    metadata_json = db.Column(JSONB, nullable=False, default=dict)


class GeographicArea(TimestampMixin, db.Model):
    __tablename__ = "geographic_areas"
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"))
    parent_id = db.Column(db.Integer, db.ForeignKey("geographic_areas.id", ondelete="RESTRICT"))
    name = db.Column(db.String(160), nullable=False)
    area_type = db.Column(db.String(40), nullable=False)  # station/ward/city/district/state
    external_id = db.Column(db.String(160))
    geometry_geojson = db.Column(JSONB)
    city = db.relationship("City", backref="geographic_areas")
    parent = db.relationship("GeographicArea", remote_side=[id], backref="children")
    __table_args__ = (
        CheckConstraint("area_type IN ('station','ward','city','district','state','other')", name="ck_geographic_areas_type"),
        Index("ix_geographic_areas_city_type", "city_id", "area_type"),
    )


class Dataset(TimestampMixin, db.Model):
    __tablename__ = "datasets"
    id = db.Column(db.Integer, primary_key=True)
    data_source_id = db.Column(db.Integer, db.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    domain = db.Column(db.String(80), nullable=False)
    source_dataset_id = db.Column(db.String(200))
    source_url = db.Column(db.Text, nullable=False)
    record_class = db.Column(db.String(30), nullable=False, default="historical")
    temporal_description = db.Column(db.String(200))
    schema_version = db.Column(db.String(80))
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    data_source = db.relationship("DataSource", backref="datasets")
    __table_args__ = (
        CheckConstraint("record_class IN ('live','historical','manually_imported','sample')", name="ck_datasets_record_class"),
        UniqueConstraint("data_source_id", "source_dataset_id", name="uq_datasets_source_id"),
        Index("ix_datasets_domain", "domain"),
    )


class DatasetCoverage(TimestampMixin, db.Model):
    __tablename__ = "dataset_coverage"
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"))
    geographic_area_id = db.Column(db.Integer, db.ForeignKey("geographic_areas.id", ondelete="RESTRICT"))
    geographic_level = db.Column(db.String(40), nullable=False)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    coverage_status = db.Column(db.String(30), nullable=False, default="unknown")
    notes = db.Column(db.Text)
    dataset = db.relationship("Dataset", backref="coverage")
    city = db.relationship("City", backref="dataset_coverage")
    geographic_area = db.relationship("GeographicArea", backref="dataset_coverage")
    __table_args__ = (Index("ix_dataset_coverage_dataset_city", "dataset_id", "city_id"),)


class DatasetFile(TimestampMixin, db.Model):
    __tablename__ = "dataset_files"
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_uri = db.Column(db.Text, nullable=False)
    checksum_sha256 = db.Column(db.String(64))
    media_type = db.Column(db.String(120))
    file_size_bytes = db.Column(db.BigInteger)
    dataset = db.relationship("Dataset", backref="files")
    __table_args__ = (UniqueConstraint("dataset_id", "checksum_sha256", name="uq_dataset_files_checksum"),)


class ImportBatch(TimestampMixin, db.Model):
    __tablename__ = "import_batches"
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    dataset_file_id = db.Column(db.Integer, db.ForeignKey("dataset_files.id", ondelete="RESTRICT"))
    status = db.Column(db.String(30), nullable=False, default="pending")
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    rows_read = db.Column(db.BigInteger)
    rows_inserted = db.Column(db.BigInteger)
    rows_rejected = db.Column(db.BigInteger)
    summary_json = db.Column(JSONB, nullable=False, default=dict)
    dataset = db.relationship("Dataset", backref="import_batches")
    raw_records = db.relationship("RawImportedRecord", backref="import_batch", cascade="all, delete-orphan", order_by="RawImportedRecord.row_number")
    __table_args__ = (Index("ix_import_batches_dataset_started", "dataset_id", "started_at"),)


class RawImportedRecord(db.Model):
    """Immutable source-shaped rows awaiting phase 4 normalization."""
    __tablename__ = "raw_imported_records"
    id = db.Column(db.BigInteger, primary_key=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    row_number = db.Column(db.Integer, nullable=False)
    row_data = db.Column(JSONB, nullable=False)
    source_reference = db.Column(db.Text, nullable=False)
    imported_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        UniqueConstraint("import_batch_id", "row_number", name="uq_raw_import_batch_row"),
        Index("ix_raw_imported_batch", "import_batch_id"),
    )


class DataRefreshLog(TimestampMixin, db.Model):
    __tablename__ = "data_refresh_logs"
    id = db.Column(db.Integer, primary_key=True)
    data_source_id = db.Column(db.Integer, db.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"))
    status = db.Column(db.String(30), nullable=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True))
    message = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)


class DataQualityReport(TimestampMixin, db.Model):
    __tablename__ = "data_quality_reports"
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("import_batches.id", ondelete="SET NULL"))
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    rows_checked = db.Column(db.BigInteger, nullable=False, default=0)
    duplicate_rows = db.Column(db.BigInteger, nullable=False, default=0)
    missing_value_counts = db.Column(JSONB, nullable=False, default=dict)
    warnings = db.Column(JSONB, nullable=False, default=list)


class MonitoringStation(TimestampMixin, db.Model):
    __tablename__ = "monitoring_stations"
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"))
    geographic_area_id = db.Column(db.Integer, db.ForeignKey("geographic_areas.id", ondelete="RESTRICT"))
    source_station_id = db.Column(db.String(200))
    name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    is_active = db.Column(db.Boolean)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    dataset = db.relationship("Dataset", backref="monitoring_stations")
    city = db.relationship("City", backref="monitoring_stations")
    __table_args__ = (
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_station_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_station_longitude"),
        UniqueConstraint("dataset_id", "source_station_id", name="uq_station_source_id"),
    )


class ObservationMixin(TimestampMixin):
    id = db.Column(db.BigInteger, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"))
    geographic_area_id = db.Column(db.Integer, db.ForeignKey("geographic_areas.id", ondelete="RESTRICT"))
    observed_at = db.Column(db.DateTime(timezone=True))
    source_record_id = db.Column(db.String(240))
    original_value = db.Column(db.Float)
    original_unit = db.Column(db.String(80))
    normalized_value = db.Column(db.Float)
    normalized_unit = db.Column(db.String(80))
    source_reference = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)


class AirQuality(ObservationMixin, db.Model):
    __tablename__ = "air_quality"
    pollutant = db.Column(db.String(40), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey("monitoring_stations.id", ondelete="RESTRICT"))
    __table_args__ = (Index("ix_air_quality_city_time", "city_id", "observed_at"), Index("ix_air_quality_pollutant_time", "pollutant", "observed_at"), UniqueConstraint("dataset_id", "source_record_id", name="uq_air_quality_dataset_record"))


class TrafficStatistics(ObservationMixin, db.Model):
    __tablename__ = "traffic_statistics"
    measure = db.Column(db.String(100), nullable=False)
    period_end = db.Column(db.Date)
    __table_args__ = (Index("ix_traffic_city_time", "city_id", "observed_at"), UniqueConstraint("dataset_id", "source_record_id", name="uq_traffic_dataset_record"))


class RoadAccident(ObservationMixin, db.Model):
    __tablename__ = "road_accidents"
    measure = db.Column(db.String(100), nullable=False)
    period_end = db.Column(db.Date)
    __table_args__ = (Index("ix_road_accidents_city_time", "city_id", "observed_at"), UniqueConstraint("dataset_id", "source_record_id", name="uq_road_accidents_dataset_record"))


class WaterStatistics(ObservationMixin, db.Model):
    __tablename__ = "water_statistics"
    measure = db.Column(db.String(100), nullable=False)
    period_end = db.Column(db.Date)
    __table_args__ = (Index("ix_water_city_time", "city_id", "observed_at"), UniqueConstraint("dataset_id", "source_record_id", name="uq_water_dataset_record"))


class PopulationStatistics(ObservationMixin, db.Model):
    __tablename__ = "population_statistics"
    indicator = db.Column(db.String(120), nullable=False)
    reference_year = db.Column(db.SmallInteger)
    __table_args__ = (Index("ix_population_city_year", "city_id", "reference_year"), UniqueConstraint("dataset_id", "source_record_id", name="uq_population_dataset_record"))


class Infrastructure(ObservationMixin, db.Model):
    __tablename__ = "infrastructure"
    asset_type = db.Column(db.String(100), nullable=False)
    asset_name = db.Column(db.String(240))
    __table_args__ = (UniqueConstraint("dataset_id", "source_record_id", name="uq_infrastructure_dataset_record"),)
