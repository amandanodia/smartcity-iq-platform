import hashlib
import csv
import logging
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO, StringIO

import numpy as np
import pandas as pd
import xlrd
from openpyxl import load_workbook
from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app import db
from app.models import DataQualityReport, Dataset, DatasetFile, ImportBatch, RawImportedRecord
from app.processing.normalize import process_import_batch

logger = logging.getLogger(__name__)
imports_bp = Blueprint("imports", __name__)
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_ROWS = 100_000


def _json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


@imports_bp.post("/import/csv")
def import_file():
    uploaded = request.files.get("file")
    dataset_id = request.form.get("dataset_id", type=int)
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": {"code": "file_required", "message": "Attach a CSV or Excel file using the file field."}}), 400
    if dataset_id is None:
        return jsonify({"error": {"code": "dataset_required", "message": "dataset_id is required."}}), 400
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        return jsonify({"error": {"code": "dataset_not_found", "message": "Dataset not found."}}), 404

    original_name = secure_filename(uploaded.filename)
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": {"code": "unsupported_file_type", "message": "Only CSV, XLSX, and XLS files are supported."}}), 415
    raw_bytes = uploaded.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
    if not raw_bytes:
        return jsonify({"error": {"code": "empty_file", "message": "The uploaded file is empty."}}), 400
    if len(raw_bytes) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": {"code": "file_too_large", "message": "Upload exceeds the configured size limit."}}), 413

    try:
        if extension == "csv":
            source_headers = next(csv.reader(StringIO(raw_bytes.decode("utf-8-sig"))), [])
        elif extension == "xls":
            workbook = xlrd.open_workbook(file_contents=raw_bytes, on_demand=True)
            try:
                source_headers = workbook.sheet_by_index(0).row_values(0)
            finally:
                workbook.release_resources()
        else:
            workbook = load_workbook(BytesIO(raw_bytes), read_only=True, data_only=True)
            try:
                source_headers = list(next(workbook.active.iter_rows(values_only=True), ()))
            finally:
                workbook.close()
        source_headers = [str(column).strip() if column is not None else "" for column in source_headers]
        if any(not column for column in source_headers) or len(set(source_headers)) != len(source_headers):
            return jsonify({"error": {"code": "invalid_columns", "message": "Column names must be non-empty and unique after trimming."}}), 422
        if extension == "csv":
            frame = pd.read_csv(BytesIO(raw_bytes), dtype=object, keep_default_na=False)
        else:
            frame = pd.read_excel(BytesIO(raw_bytes), dtype=object, keep_default_na=False)
    except Exception as exc:
        logger.info("Import parsing rejected file %s: %s", original_name, exc)
        return jsonify({"error": {"code": "parse_error", "message": "File could not be parsed as a supported tabular sheet."}}), 422

    if frame.empty or len(frame.columns) == 0:
        return jsonify({"error": {"code": "no_records", "message": "The file contains no data rows or columns."}}), 422
    if len(frame) > MAX_ROWS:
        return jsonify({"error": {"code": "too_many_rows", "message": f"Maximum supported rows per import is {MAX_ROWS}."}}), 413
    columns = source_headers
    if len(columns) != len(frame.columns):
        return jsonify({"error": {"code": "invalid_columns", "message": "Column names must be non-empty and unique after trimming."}}), 422
    frame.columns = columns

    checksum = hashlib.sha256(raw_bytes).hexdigest()
    existing_file = DatasetFile.query.filter_by(dataset_id=dataset.id, checksum_sha256=checksum).one_or_none()
    if existing_file is not None:
        return jsonify({"error": {"code": "duplicate_file", "message": "This exact file has already been imported for the dataset.", "dataset_file_id": existing_file.id}}), 409
    duplicate_count = int(frame.duplicated(keep="first").sum())
    missing_counts = {str(column): int(frame[column].replace("", np.nan).isna().sum()) for column in frame.columns}
    upload_id = uuid.uuid4().hex
    storage_dir = os.path.abspath(current_app.config["IMPORT_STORAGE_DIR"])
    os.makedirs(storage_dir, exist_ok=True)
    stored_path = os.path.join(storage_dir, f"{upload_id}.{extension}")
    source_reference = dataset.source_url
    # The ingestion path is explicitly a user-supplied file, regardless of
    # whether the underlying source describes current or historical periods.
    dataset.record_class = "manually_imported"
    batch = None
    try:
        with open(stored_path, "wb") as output:
            output.write(raw_bytes)
        dataset_file = DatasetFile(dataset_id=dataset.id, original_filename=original_name,
                                   storage_uri=stored_path, checksum_sha256=checksum,
                                   media_type=uploaded.mimetype, file_size_bytes=len(raw_bytes))
        db.session.add(dataset_file)
        db.session.flush()
        batch = ImportBatch(dataset_id=dataset.id, dataset_file_id=dataset_file.id,
                            status="staged", started_at=datetime.now(timezone.utc),
                            rows_read=len(frame), rows_inserted=len(frame), rows_rejected=0,
                            summary_json={"stage": "raw", "columns": columns, "duplicate_rows_detected": duplicate_count})
        db.session.add(batch)
        db.session.flush()
        # Preserve each source-shaped row exactly as text/object data. Phase 4
        # will add validated, normalized domain observations.
        records = []
        for offset, row in enumerate(frame.to_dict(orient="records"), start=2):
            row_data = {str(key): _json_value(value) for key, value in row.items()}
            records.append(RawImportedRecord(import_batch_id=batch.id, row_number=offset,
                                             row_data=row_data, source_reference=source_reference))
        db.session.add_all(records)
        db.session.add(DataQualityReport(dataset_id=dataset.id, import_batch_id=batch.id,
                                         rows_checked=len(frame), duplicate_rows=duplicate_count,
                                         missing_value_counts=missing_counts,
                                         warnings=["Rows are staged as source-shaped raw data; domain normalization has not run."] + (["Exact duplicate rows were detected and retained."] if duplicate_count else [])))
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.exists(stored_path):
            os.remove(stored_path)
        logger.exception("Import persistence failed for dataset_id=%s", dataset.id)
        return jsonify({"error": {"code": "import_failed", "message": "The import could not be stored."}}), 500

    return jsonify({"data": {"import_batch_id": batch.id, "dataset_id": dataset.id,
                              "record_class": "manually_imported", "status": batch.status,
                              "rows_read": len(frame), "rows_staged": len(frame),
                              "duplicate_rows_detected": duplicate_count, "columns": columns,
                              "source_reference": source_reference,
                              "message": "Raw rows were staged. They are not normalized or included in analytics."}}), 201


@imports_bp.post("/import-batches/<int:batch_id>/process")
def normalize_import(batch_id):
    batch = db.session.get(ImportBatch, batch_id)
    if batch is None:
        return jsonify({"error": {"code": "import_batch_not_found", "message": "Import batch not found."}}), 404
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("mapping"), dict):
        return jsonify({"error": {"code": "invalid_mapping", "message": "Request JSON must include a mapping object."}}), 400
    try:
        result = process_import_batch(batch, payload["mapping"])
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": "invalid_import_mapping", "message": str(exc)}}), 422
    except Exception:
        db.session.rollback()
        logger.exception("Import normalization failed for batch_id=%s", batch_id)
        return jsonify({"error": {"code": "normalization_failed", "message": "The import batch could not be normalized."}}), 500
    return jsonify({"data": {"import_batch_id": batch_id, **result}})
