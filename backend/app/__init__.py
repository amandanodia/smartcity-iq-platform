import os
import logging

from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/smartcity_iq"
    )
    # Render supplies postgres:// or postgresql:// URLs; use the installed psycopg 3 driver.
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_IMPORT_BYTES", str(20 * 1024 * 1024))),
        IMPORT_STORAGE_DIR=os.getenv("IMPORT_STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "uploads")),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    # Import model metadata before Alembic inspects the database.
    from app import models  # noqa: F401

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    from app.api import register_blueprints
    register_blueprints(app)

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": {"code": "file_too_large", "message": "Upload exceeds the configured size limit."}}), 413

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": {"code": error.name.lower().replace(" ", "_"), "message": error.description}}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled API error", exc_info=error)
        return jsonify({"error": {"code": "internal_error", "message": "The request could not be completed."}}), 500

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            return jsonify({"status": "error", "database": "unavailable"}), 503
        return jsonify({"status": "ok", "database": "connected"})

    return app
