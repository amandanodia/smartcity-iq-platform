from .catalog import catalog_bp
from .analytics import analytics_bp
from .imports import imports_bp


def register_blueprints(app):
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(imports_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp, url_prefix="/api")
