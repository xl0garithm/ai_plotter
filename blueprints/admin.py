"""Admin blueprint for queue management."""

from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
def dashboard():
    """Render the admin dashboard."""
    return render_template("admin.html")

