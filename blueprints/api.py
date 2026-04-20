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
    ChessMoveData,
    _validate_square,
    chess_board_to_svg,
    generate_chess_board,
    generate_chess_demo_gcode,
    generate_chess_demo_svg,
    generate_move_gcode,
    generate_pick_place_demo_gcode,
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
    config = current_app.config
    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}
    
    current_app.logger.info("Health check requested")
    
    return jsonify({
        "status": "ok",
        "dry_run": dry_run,
        "serial_port": config.get("SERIAL_PORT", "not configured"),
        "chess_board_size_mm": config.get("CHESS_BOARD_SIZE_MM", 215.9),
    })


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
        board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 215.9),
        square_count=config.get("CHESS_SQUARE_COUNT", 8),
        gap_mm=config.get("CHESS_GAP_MM", 2.0),
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
        board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 215.9),
        square_count=config.get("CHESS_SQUARE_COUNT", 8),
        gap_mm=config.get("CHESS_GAP_MM", 2.0),
        origin_x=config.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=config.get("CHESS_ORIGIN_Y_MM", 0.0),
        tap_dwell_s=config.get("CHESS_TAP_DWELL_S", 0.3),
        magnet_on_cmd=config.get("CHESS_MAGNET_ON_GCODE", "M3 S255"),
        magnet_off_cmd=config.get("CHESS_MAGNET_OFF_GCODE", "M3 S0\nM5"),
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


@api_bp.post("/chess/home")
def chess_home() -> Response:
    """Home the chess robot carriage to X0/Y0 using rehome sequence."""
    config = current_app.config

    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    if dry_run:
        return jsonify({"success": True, "dry_run": True})

    try:
        controller = PlotterController(
            port=config["SERIAL_PORT"],
            baudrate=config["SERIAL_BAUDRATE"],
            timeout=config.get("SERIAL_TIMEOUT", 10.0),
            line_delay=config.get("PLOTTER_LINE_DELAY", 0.1),
        )
        controller.connect()
        try:
            controller.rehome()
        finally:
            controller.disconnect()

        return jsonify({"success": True})
    except PlotterError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chess home failed: %s", exc)
        return jsonify({"error": "Unexpected error during homing."}), 500


@api_bp.post("/chess/pick-place-demo")
def chess_pick_place_demo() -> Response:
    """Run a simple pick-and-place demo using hardware reset to kill the magnet.

    Phase 1: rapid to source, magnet on, carry to target.
    Reset: disconnect+reconnect toggles DTR, resetting Arduino and killing PWM.
    Phase 2: return home.

    Optional JSON body: {"from": "e2", "to": "e4"}
    Defaults to e2 -> e4 if not provided.
    """
    config = current_app.config
    data = request.get_json(silent=True) or {}
    from_sq = data.get("from", "e2").strip().lower()
    to_sq = data.get("to", "e4").strip().lower()

    if not _validate_square(from_sq) or not _validate_square(to_sq):
        return jsonify({"error": f"Invalid square: {from_sq} or {to_sq}"}), 400

    carry_lines, return_lines, stats = generate_pick_place_demo_gcode(
        from_sq=from_sq,
        to_sq=to_sq,
        board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 215.9),
        square_count=config.get("CHESS_SQUARE_COUNT", 8),
        gap_mm=config.get("CHESS_GAP_MM", 2.0),
        origin_x=config.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=config.get("CHESS_ORIGIN_Y_MM", 0.0),
        mirror_ranks=config.get("CHESS_MIRROR_RANKS", False),
        magnet_on_cmd=config.get("CHESS_MAGNET_ON_GCODE", "M3 S255"),
        engage_dwell=config.get("CHESS_MAGNET_ENGAGE_DWELL_S", 0.3),
        move_feed_rate=config.get("CHESS_MOVE_FEED_RATE", 3000),
    )

    all_lines = carry_lines + ["; --- RESET (magnet off) ---"] + return_lines

    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    if dry_run:
        return jsonify({
            "success": True,
            "dry_run": True,
            "stats": stats,
            "gcode_lines": all_lines,
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
            # Phase 1: pick up and carry with magnet on
            controller.send_gcode_lines(carry_lines)
            # Reset Arduino to kill magnet (DTR toggle)
            controller.reset()
            # Phase 2: return home
            controller.send_gcode_lines(return_lines)
        finally:
            controller.disconnect()

        return jsonify({
            "success": True,
            "stats": stats,
            "gcode_lines": all_lines,
        })
    except PlotterError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Pick-place demo failed: %s", exc)
        return jsonify({"error": "Unexpected error during pick-place demo."}), 500


@api_bp.post("/chess/move")
def chess_move() -> Response:
    """Execute a chess move on the physical board.

    Accepts chess.js verbose move format and translates to pick-and-place G-code.
    """
    config = current_app.config
    data = request.get_json(silent=True)
    
    current_app.logger.info("=" * 50)
    current_app.logger.info("CHESS MOVE REQUEST RECEIVED")
    current_app.logger.info("=" * 50)
    current_app.logger.info("Request data: %s", data)
    
    if not data:
        current_app.logger.warning("No JSON body in request")
        return jsonify({"error": "JSON body required."}), 400

    # Validate required fields
    from_sq = data.get("from", "").strip().lower()
    to_sq = data.get("to", "").strip().lower()
    piece = data.get("piece", "").strip().lower()
    color = data.get("color", "").strip().lower()
    flags = data.get("flags", "")
    captured = data.get("captured") or None
    promotion = data.get("promotion") or None
    capture_index = data.get("capture_index", 0)

    current_app.logger.info("Parsed move: %s %s -> %s (color: %s, flags: '%s', captured: %s, promotion: %s)",
                          piece, from_sq, to_sq, color, flags, captured, promotion)

    if not from_sq or not to_sq:
        current_app.logger.warning("Missing from/to squares: from='%s', to='%s'", from_sq, to_sq)
        return jsonify({"error": "'from' and 'to' squares are required."}), 400
    if not _validate_square(from_sq) or not _validate_square(to_sq):
        current_app.logger.warning("Invalid squares: from='%s', to='%s'", from_sq, to_sq)
        return jsonify({"error": f"Invalid square: {from_sq} or {to_sq}"}), 400
    if not piece or piece not in "pnbrqk":
        current_app.logger.warning("Invalid piece: '%s'", piece)
        return jsonify({"error": f"Invalid piece: {piece}"}), 400
    if color not in ("w", "b"):
        current_app.logger.warning("Invalid color: '%s'", color)
        return jsonify({"error": f"Invalid color: {color}"}), 400
    if not isinstance(capture_index, int) or capture_index < 0:
        current_app.logger.warning("Invalid capture_index: %s", capture_index)
        return jsonify({"error": "capture_index must be a non-negative integer."}), 400

    move = ChessMoveData(
        from_sq=from_sq,
        to_sq=to_sq,
        piece=piece,
        color=color,
        captured=captured,
        flags=flags,
        promotion=promotion,
        capture_index=capture_index,
    )

    current_app.logger.info("Move object created: %s", move)

    try:
        current_app.logger.info("Generating G-code for move %s %s -> %s...", piece, from_sq, to_sq)
        phases, stats = generate_move_gcode(
            move,
            board_size_mm=config.get("CHESS_BOARD_SIZE_MM", 215.9),
            square_count=config.get("CHESS_SQUARE_COUNT", 8),
            gap_mm=config.get("CHESS_GAP_MM", 2.0),
            origin_x=config.get("CHESS_ORIGIN_X_MM", 0.0),
            origin_y=config.get("CHESS_ORIGIN_Y_MM", 0.0),
            mirror_ranks=config.get("CHESS_MIRROR_RANKS", False),
            magnet_on_cmd=config.get("CHESS_MAGNET_ON_GCODE", "M3 S255"),
            magnet_off_cmd=config.get("CHESS_MAGNET_OFF_GCODE", "M3 S0\nM5"),
            engage_dwell=config.get("CHESS_MAGNET_ENGAGE_DWELL_S", 0.3),
            release_dwell=config.get("CHESS_MAGNET_RELEASE_DWELL_S", 0.3),
            move_feed_rate=config.get("CHESS_MOVE_FEED_RATE", 3000),
            capture_x=config.get("CHESS_CAPTURE_X_MM", -30.0),
            capture_y=config.get("CHESS_CAPTURE_Y_MM", 0.0),
            capture_spacing=config.get("CHESS_CAPTURE_SPACING_MM", 15.0),
        )
        current_app.logger.info("G-code generated: %d phases, stats=%s", len(phases), stats)
    except (ValueError, IndexError) as exc:
        current_app.logger.error("G-code generation failed: %s", exc)
        return jsonify({"error": f"Move generation failed: {exc}"}), 400

    # Flatten for dry-run / response display
    all_lines: list[str] = []
    for phase in phases:
        all_lines.extend(phase)

    current_app.logger.info("Total G-code lines: %d", len(all_lines))

    dry_run = config.get("PLOTTER_DRY_RUN", False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    current_app.logger.info("Dry run mode: %s", dry_run)

    if dry_run:
        current_app.logger.info("DRY RUN - returning G-code without executing")
        current_app.logger.info("G-code preview (first 10 lines):\n%s", "\n".join(all_lines[:10]))
        return jsonify({
            "success": True,
            "dry_run": True,
            "stats": stats,
            "gcode_lines": all_lines,
        })

    try:
        current_app.logger.info("Connecting to plotter on port: %s", config["SERIAL_PORT"])
        controller = PlotterController(
            port=config["SERIAL_PORT"],
            baudrate=config["SERIAL_BAUDRATE"],
            timeout=config.get("SERIAL_TIMEOUT", 10.0),
            line_delay=config.get("PLOTTER_LINE_DELAY", 0.1),
        )
        controller.connect()
        try:
            for i, phase in enumerate(phases):
                current_app.logger.info("Executing phase %d/%d...", i + 1, len(phases))
                controller.send_gcode_lines(phase)
            if config.get("CHESS_HOME_AFTER_MOVE", False):
                current_app.logger.info("Homing after move (CHESS_HOME_AFTER_MOVE=true)")
                controller.rehome()
            current_app.logger.info("All phases executed successfully")
        finally:
            controller.disconnect()
            current_app.logger.info("Plotter disconnected")

        current_app.logger.info("CHESS MOVE COMPLETED SUCCESSFULLY")
        return jsonify({
            "success": True,
            "stats": stats,
            "gcode_lines": all_lines,
        })
    except PlotterError as exc:
        current_app.logger.error("Plotter error: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chess move failed: %s", exc)
        return jsonify({"error": "Unexpected error during move."}), 500
