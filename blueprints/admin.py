"""Admin blueprint for queue management."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def require_login():
    """Restrict access to admin routes."""
    if request.endpoint == "admin.login":
        return None

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle admin login."""
    if request.method == "POST":
        pin = request.form.get("pin")
        expected_pin = current_app.config.get("ADMIN_PIN", "1234")

        if pin == expected_pin:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))

        flash("Invalid PIN")

    return render_template("admin_login.html")


@admin_bp.get("/logout")
def logout():
    """Log out the admin."""
    session.pop("admin_logged_in", None)
    return redirect(url_for("web.index"))


@admin_bp.get("/")
def dashboard():
    """Render the admin dashboard."""
    return render_template("admin.html")
