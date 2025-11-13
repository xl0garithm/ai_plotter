"""API blueprint for AJAX endpoints."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request, send_file

from services.gemini_client import GeminiClient, GeminiClientError
from services.queue import (
    QueueError,
    approve_job,
    cancel_job,
    confirm_job,
    create_job_from_upload,
    get_generated_image_path,
    get_job,
    list_jobs,
    start_print_job,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


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
    prompt = request.form.get("prompt")
    requester = request.form.get("requester") or request.remote_addr

    try:
        job = create_job_from_upload(
            image,
            prompt=prompt,
            requester=requester,
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

