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

import tempfile
from pathlib import Path

from services.chess import (
    chess_board_to_svg,
    generate_chess_board,
    generate_chess_demo_gcode,
    generate_chess_demo_svg,
    generate_piece_move_gcode,
)
from services.electromagnet import create_electromagnet_from_mapping
from services.gcode import vector_data_to_gcode, GCodeSettings, GCodeError
from services.gemini_client import GeminiClient, GeminiClientError
from services.plotter import PlotterController, PlotterError
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


@api_bp.get("/chess/preview")
def chess_preview() -> Response:
    """Return SVG preview of chess board."""
    board_size = request.args.get("size", 800, type=int)
    hatch_spacing = request.args.get("hatch_spacing", 6.0, type=float)

    vector_data = generate_chess_board(
        board_size=board_size,
        hatch_spacing=hatch_spacing,
    )
    svg_content = chess_board_to_svg(vector_data)

    return Response(svg_content, mimetype="image/svg+xml")


@api_bp.post("/chess/print")
def chess_print() -> Response:
    """Generate chess board and send to plotter."""
    config = current_app.config

    data = request.get_json(silent=True) or {}
    board_size = data.get("board_size", 800)
    hatch_spacing = data.get("hatch_spacing", 6.0)

    try:
        vector_data = generate_chess_board(
            board_size=board_size,
            hatch_spacing=hatch_spacing,
        )

        # 100mm target physical size
        target_size_mm = 100.0
        pixel_size_mm = target_size_mm / board_size

        settings = GCodeSettings(
            pixel_size_mm=pixel_size_mm,
            feed_rate=config.get("PLOTTER_FEED_RATE", 5000),
            pen_dwell_seconds=0.05,
        )

        # Generate G-code to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gcode", delete=False
        ) as tmp:
            gcode_path = Path(tmp.name)

        stats = vector_data_to_gcode(vector_data, gcode_path, settings)

        # Check dry-run mode
        dry_run = config.get("PLOTTER_DRY_RUN", False)
        if isinstance(dry_run, str):
            dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

        if dry_run:
            gcode_path.unlink(missing_ok=True)
            return jsonify({
                "success": True,
                "dry_run": True,
                "stats": {
                    "path_count": stats.path_count,
                    "estimated_seconds": round(stats.estimated_seconds, 1),
                },
            })

        # Send to plotter
        controller = PlotterController(
            port=config["SERIAL_PORT"],
            baudrate=config["SERIAL_BAUDRATE"],
            timeout=config.get("SERIAL_TIMEOUT", 10.0),
            line_delay=config.get("PLOTTER_LINE_DELAY", 0.1),
        )

        try:
            controller.connect()
            with gcode_path.open("r", encoding="utf-8") as f:
                gcode_lines = f.readlines()
            controller.send_gcode_lines(gcode_lines)
            return jsonify({
                "success": True,
                "stats": {
                    "path_count": stats.path_count,
                    "estimated_seconds": round(stats.estimated_seconds, 1),
                },
            })
        finally:
            controller.disconnect()
            gcode_path.unlink(missing_ok=True)

    except GCodeError as exc:
        return jsonify({"error": str(exc)}), 500
    except PlotterError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chess print failed: %s", exc)
        return jsonify({"error": "Unexpected error during printing."}), 500


@api_bp.get("/chess/demo/preview")
def chess_demo_preview() -> Response:
    """Return SVG preview of the chess demo traversal."""
    config = current_app.config
    svg_content = generate_chess_demo_svg(
        board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 200.0),
        square_count=config.get("CHESS_SQUARE_COUNT", 8),
        origin_x=config.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=config.get("CHESS_ORIGIN_Y_MM", 0.0),
    )
    return Response(svg_content, mimetype="image/svg+xml")


@api_bp.post("/chess/execute-move")
def chess_execute_move() -> Response:
    """Run a single piece move on the plotter with Pi electromagnet timing."""
    config = current_app.config

    data = request.get_json(silent=True) or {}
    from_sq = (data.get("from") or "").strip().lower()
    to_sq = (data.get("to") or "").strip().lower()

    if len(from_sq) != 2 or len(to_sq) != 2:
        return jsonify({"error": "from and to must be algebraic squares (e.g. e2, e4)."}), 400

    try:
        gcode_lines = generate_piece_move_gcode(
            from_sq,
            to_sq,
            board_size_mm=float(config.get("CHESS_BOARD_SIZE_MM", 200.0)),
            square_count=int(config.get("CHESS_SQUARE_COUNT", 8)),
            origin_x=float(config.get("CHESS_ORIGIN_X_MM", 0.0)),
            origin_y=float(config.get("CHESS_ORIGIN_Y_MM", 0.0)),
            source_settle_s=float(config.get("CHESS_SOURCE_SETTLE_S", 0.05)),
            pickup_dwell_s=float(config.get("CHESS_PICKUP_DWELL_S", 0.2)),
            place_dwell_s=float(config.get("CHESS_PLACE_DWELL_S", 0.15)),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    if dry_run:
        return jsonify({
            "success": True,
            "dry_run": True,
            "gcode_lines": gcode_lines,
        })

    electromagnet = create_electromagnet_from_mapping(config)
    try:
        controller = PlotterController(
            port=config["SERIAL_PORT"],
            baudrate=config["SERIAL_BAUDRATE"],
            timeout=config.get("SERIAL_TIMEOUT", 10.0),
            line_delay=config.get("PLOTTER_LINE_DELAY", 0.1),
        )
        controller.connect()
        try:
            controller.send_gcode_lines(gcode_lines, electromagnet=electromagnet)
        finally:
            controller.disconnect()
    except PlotterError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chess execute-move failed: %s", exc)
        return jsonify({"error": "Unexpected error during move."}), 500
    finally:
        electromagnet.close()

    return jsonify({"success": True})


@api_bp.post("/chess/demo/run")
def chess_demo_run() -> Response:
    """Generate chess demo G-code and send to plotter."""
    config = current_app.config

    gcode_lines, stats = generate_chess_demo_gcode(
        board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 200.0),
        square_count=config.get("CHESS_SQUARE_COUNT", 8),
        origin_x=config.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=config.get("CHESS_ORIGIN_Y_MM", 0.0),
        tap_dwell_s=config.get("CHESS_TAP_DWELL_S", 0.3),
    )

    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    if dry_run:
        return jsonify({
            "success": True,
            "dry_run": True,
            "stats": stats,
        })

    try:
        controller = PlotterController(
            port=config["SERIAL_PORT"],
            baudrate=config["SERIAL_BAUDRATE"],
            timeout=config.get("SERIAL_TIMEOUT", 10.0),
            line_delay=config.get("PLOTTER_LINE_DELAY", 0.1),
        )
        controller.connect()
        try:
            controller.send_gcode_lines(gcode_lines)
        finally:
            controller.disconnect()

        return jsonify({
            "success": True,
            "stats": stats,
        })
    except PlotterError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chess demo run failed: %s", exc)
        return jsonify({"error": "Unexpected error during demo."}), 500
