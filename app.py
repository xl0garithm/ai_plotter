"""Flask application factory for the AI plotter."""

from __future__ import annotations

from flask import Flask

from config import Config
from services.database import init_db


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    # Ensure storage directories exist
    config_class.ensure_directories()

    # Initialise database
    init_db(app.config["DATABASE_URL"])

    # Register blueprints
    from blueprints.web import web_bp
    from blueprints.admin import admin_bp
    from blueprints.api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()

