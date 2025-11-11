"""Frontend blueprint for user interactions."""

from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    """Render main capture interface."""
    return render_template("index.html")

