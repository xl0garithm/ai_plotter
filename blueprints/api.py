"""API blueprint for AJAX endpoints."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    send_file,
    session,
)

from services.gemini_client import GeminiClient, GeminiClientError
from services.queue import (
    QueueError,
    approve_job,
    cancel_job,
    confirm_job,
    create_job_from_manual_upload,
    create_job_from_upload,
    get_generated_image_path,
    get_job,
    list_jobs,
    start_print_job,
)
from services.style_presets import DEFAULT_STYLE_KEY, get_style

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.before_request
def require_admin_api():
    """Restrict access to admin API routes."""
    if request.path.startswith("/api/admin"):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401


def _gemini_client() -> GeminiClient:
    config = current_app.config
    return GeminiClient(
        api_key=config["GEMINI_API_KEY"],
        model=config["GEMINI_MODEL"],
        endpoint=config.get("GEMINI_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta"),
        timeout=int(config.get("GEMINI_TIMEOUT", 60)),
    )


@api_bp.get("/health")
def health_check() -> Response:
    """Return application health status."""
    return jsonify({"status": "ok"})


@api_bp.post("/jobs")
def submit_job() -> Response:
    """Create a new job from an uploaded image."""
    image = request.files.get("image")
    custom_prompt = (request.form.get("prompt") or "").strip() or None
    style_key = (request.form.get("style") or DEFAULT_STYLE_KEY).strip().lower()
    email = (request.form.get("email") or "").strip() or None
    requester = request.form.get("requester") or request.remote_addr

    if email and "@" not in email:
        return jsonify({"error": "Please provide a valid email address."}), 400

    style = get_style(style_key)
    try:
        job = create_job_from_upload(
            image,
            prompt=custom_prompt,
            requester=requester,
            email=email,
            style_key=style_key,
            style_prompt=style["prompt"],
            config=current_app.config,
            gemini_client=_gemini_client(),
        )
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GeminiClientError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Unhandled error during job submission: %s", exc)
        return jsonify({"error": "Unexpected server error."}), 500

    return jsonify({"job_id": job["id"], "status": job["status"]})


@api_bp.get("/jobs")
def list_public_jobs() -> Response:
    """Return public job statuses."""
    jobs = list_jobs(admin=False, limit=25)
    return jsonify(jobs)


@api_bp.get("/jobs/<int:job_id>")
def get_public_job(job_id: int) -> Response:
    """Return a single job status."""
    try:
        job = get_job(job_id, admin=False)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(job)


@api_bp.get("/jobs/<int:job_id>/preview")
def job_preview(job_id: int):
    """Return the generated image preview."""
    try:
        image_path = get_generated_image_path(job_id)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 404
    return send_file(image_path, mimetype="image/png")


@api_bp.post("/jobs/<int:job_id>/confirm")
def job_confirm(job_id: int) -> Response:
    """Confirm a job for the queue."""
    try:
        job = confirm_job(job_id)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(job)


@api_bp.delete("/jobs/<int:job_id>")
def job_cancel(job_id: int) -> Response:
    """Cancel a job."""
    try:
        job = cancel_job(job_id)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(job)


@api_bp.get("/admin/jobs")
def admin_jobs() -> Response:
    """Return job list for admin view."""
    jobs = list_jobs(admin=True, limit=50)
    return jsonify(jobs)


@api_bp.post("/admin/jobs/<int:job_id>/approve")
def admin_approve(job_id: int) -> Response:
    """Approve job for plotting."""
    try:
        job = approve_job(job_id)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(job)


@api_bp.post("/admin/jobs/<int:job_id>/start")
def admin_start(job_id: int) -> Response:
    """Queue job for printing."""
    try:
        allow_reprint = request.args.get("reprint") in {"1", "true", "yes", "on"}
        job = start_print_job(job_id, current_app.config, allow_reprint=allow_reprint)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Unexpected error during print start: %s", exc)
        return jsonify({"error": "Failed to start print job."}), 500
    return jsonify(job)


@api_bp.post("/admin/jobs/<int:job_id>/cancel")
def admin_cancel(job_id: int) -> Response:
    """Cancel a job from the admin panel."""
    try:
        job = cancel_job(job_id)
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(job)


@api_bp.post("/admin/uploads")
def admin_manual_upload() -> Response:
    """Upload an outline image directly for plotting."""
    image = request.files.get("image")
    requester = request.remote_addr

    try:
        job = create_job_from_manual_upload(
            image,
            requester=requester,
            config=current_app.config,
        )
    except QueueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Manual upload failed: %s", exc)
        return jsonify({"error": "Failed to ingest manual upload."}), 500

    return jsonify(job)
