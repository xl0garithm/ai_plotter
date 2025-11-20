"""Frontend blueprint for user interactions."""

from flask import Blueprint, render_template

from services.style_presets import get_ui_style_map

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    """Render main capture interface."""
    return render_template("index.html", style_presets=get_ui_style_map())

