"""API routes: jobs, chess, admin."""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path

import chess
from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from dependencies import get_config, require_admin_api
from services.chess import (
    chess_board_to_svg,
    generate_chess_board,
    generate_chess_demo_gcode,
    generate_chess_demo_svg,
    move_to_gcode,
    uci_square_to_mm,
)
from services.chess_game import get_session
from services.gcode import GCodeError, GCodeSettings, vector_data_to_gcode
from services.plotter import PlotterController, PlotterError
from services.queue import (
    QueueError,
    approve_job,
    cancel_job,
    confirm_job,
    create_job_from_manual_upload,
    get_generated_image_path,
    get_job,
    list_jobs,
    start_print_job,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _config_dict(request: Request):
    c = get_config()
    return {
        "SERIAL_PORT": c.SERIAL_PORT,
        "SERIAL_BAUDRATE": c.SERIAL_BAUDRATE,
        "SERIAL_TIMEOUT": c.SERIAL_TIMEOUT,
        "PLOTTER_DRY_RUN": c.PLOTTER_DRY_RUN,
        "PLOTTER_LINE_DELAY": c.PLOTTER_LINE_DELAY,
        "PLOTTER_FEED_RATE": c.PLOTTER_FEED_RATE,
        "CHESS_BOARD_SIZE_MM": c.CHESS_BOARD_SIZE_MM,
        "CHESS_SQUARE_COUNT": c.CHESS_SQUARE_COUNT,
        "CHESS_ORIGIN_X_MM": c.CHESS_ORIGIN_X_MM,
        "CHESS_ORIGIN_Y_MM": c.CHESS_ORIGIN_Y_MM,
        "CHESS_DISCARD_OFFSET_SQUARES": getattr(c, "CHESS_DISCARD_OFFSET_SQUARES", 1.5),
        "CHESS_TAP_DWELL_S": c.CHESS_TAP_DWELL_S,
        "CHESS_MAGNET_SETTLE_S": c.CHESS_MAGNET_SETTLE_S,
        "ENABLE_MANUAL_UPLOAD": getattr(c, "ENABLE_MANUAL_UPLOAD", False),
        "UPLOAD_DIR": c.UPLOAD_DIR,
        "GENERATED_DIR": c.GENERATED_DIR,
        "GCODE_DIR": c.GCODE_DIR,
        "VECTOR_RESOLUTION": getattr(c, "VECTOR_RESOLUTION", 1600),
        "VECTORIZE_THRESHOLD": getattr(c, "VECTORIZE_THRESHOLD", 240),
        "VECTORIZE_SIMPLIFY_PX": getattr(c, "VECTORIZE_SIMPLIFY_PX", 2.0),
        "VECTORIZE_MIN_POINTS": getattr(c, "VECTORIZE_MIN_POINTS", 24),
        "VECTORIZE_DOWNSAMPLE_STEP": getattr(c, "VECTORIZE_DOWNSAMPLE_STEP", 1),
        "VECTORIZE_STROKE_WIDTH": getattr(c, "VECTORIZE_STROKE_WIDTH", 3.0),
        "VECTORIZE_CROP_PADDING_RATIO": getattr(c, "VECTORIZE_CROP_PADDING_RATIO", 0.05),
    }


# --- Public API ---


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/jobs")
def list_public_jobs():
    return list_jobs(admin=False, limit=25)


@router.get("/jobs/{job_id}")
def get_public_job(job_id: int):
    try:
        return get_job(job_id, admin=False)
    except QueueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/jobs/{job_id}/preview")
def job_preview(job_id: int):
    try:
        path = get_generated_image_path(job_id)
        return FileResponse(path, media_type="image/png")
    except QueueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/jobs/{job_id}/confirm")
def job_confirm(job_id: int):
    try:
        return confirm_job(job_id)
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jobs/{job_id}")
def job_cancel(job_id: int):
    try:
        return cancel_job(job_id)
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Admin API (require login) ---


@router.get("/admin/jobs")
def admin_jobs(_: None = Depends(require_admin_api)):
    return list_jobs(admin=True, limit=50)


@router.post("/admin/jobs/{job_id}/approve")
def admin_approve(job_id: int, _: None = Depends(require_admin_api)):
    try:
        return approve_job(job_id)
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/jobs/{job_id}/start")
def admin_start(
    job_id: int,
    request: Request,
    _: None = Depends(require_admin_api),
):
    reprint = request.query_params.get("reprint") in {"1", "true", "yes", "on"}
    config = get_config()
    try:
        return start_print_job(job_id, config, allow_reprint=reprint)
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during print start: %s", e)
        raise HTTPException(status_code=500, detail="Failed to start print job.")


@router.post("/admin/jobs/{job_id}/cancel")
def admin_cancel(job_id: int, _: None = Depends(require_admin_api)):
    try:
        return cancel_job(job_id)
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/uploads")
async def admin_manual_upload(
    request: Request,
    image: UploadFile = File(...),
    _: None = Depends(require_admin_api),
):
    config = get_config()
    content = await image.read()
    if not content or not image.filename:
        raise HTTPException(status_code=400, detail="No image provided.")
    # Adapter: (bytes, filename) for queue
    try:
        job = create_job_from_manual_upload(
            (content, image.filename or "upload.png"),
            requester=request.client.host if request.client else "unknown",
            config=config,
        )
        return job
    except QueueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Manual upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to ingest manual upload.")


# --- Chess preview / print ---


@router.get("/chess/preview")
def chess_preview(size: int = 800, hatch_spacing: float = 6.0):
    vector_data = generate_chess_board(board_size=size, hatch_spacing=hatch_spacing)
    svg_content = chess_board_to_svg(vector_data)
    return Response(content=svg_content, media_type="image/svg+xml")


@router.post("/chess/print")
async def chess_print(request: Request, body: dict | None = Body(default=None)):
    config = get_config()
    body = body or {}
    board_size = body.get("board_size", 800)
    hatch_spacing = body.get("hatch_spacing", 6.0)
    try:
        vector_data = generate_chess_board(
            board_size=board_size,
            hatch_spacing=hatch_spacing,
        )
        target_size_mm = 100.0
        pixel_size_mm = target_size_mm / board_size
        cfg = _config_dict(request)
        settings = GCodeSettings(
            pixel_size_mm=pixel_size_mm,
            feed_rate=cfg.get("PLOTTER_FEED_RATE", 5000),
            pen_dwell_seconds=0.05,
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", delete=False) as tmp:
            gcode_path = Path(tmp.name)
        stats = vector_data_to_gcode(vector_data, gcode_path, settings)
        dry_run = config.PLOTTER_DRY_RUN
        if dry_run:
            gcode_path.unlink(missing_ok=True)
            return {
                "success": True,
                "dry_run": True,
                "stats": {
                    "path_count": stats.path_count,
                    "estimated_seconds": round(stats.estimated_seconds, 1),
                },
            }
        controller = PlotterController(
            port=config.SERIAL_PORT,
            baudrate=config.SERIAL_BAUDRATE,
            timeout=getattr(config, "SERIAL_TIMEOUT", 10.0),
            line_delay=config.PLOTTER_LINE_DELAY,
        )
        try:
            controller.connect()
            with gcode_path.open("r", encoding="utf-8") as f:
                gcode_lines = f.readlines()
            controller.send_gcode_lines(gcode_lines)
            return {
                "success": True,
                "stats": {
                    "path_count": stats.path_count,
                    "estimated_seconds": round(stats.estimated_seconds, 1),
                },
            }
        finally:
            controller.disconnect()
            gcode_path.unlink(missing_ok=True)
    except GCodeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except PlotterError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Chess print failed: %s", e)
        raise HTTPException(status_code=500, detail="Unexpected error during printing.")


@router.get("/chess/demo/preview")
def chess_demo_preview(request: Request):
    cfg = _config_dict(request)
    svg_content = generate_chess_demo_svg(
        board_size_mm=cfg.get("CHESS_BOARD_SIZE_MM", 200.0),
        square_count=cfg.get("CHESS_SQUARE_COUNT", 8),
        origin_x=cfg.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=cfg.get("CHESS_ORIGIN_Y_MM", 0.0),
    )
    return Response(content=svg_content, media_type="image/svg+xml")


@router.post("/chess/demo/run")
def chess_demo_run(request: Request):
    config = get_config()
    cfg = _config_dict(request)
    gcode_lines, stats = generate_chess_demo_gcode(
        board_size_mm=cfg.get("CHESS_BOARD_SIZE_MM", 200.0),
        square_count=cfg.get("CHESS_SQUARE_COUNT", 8),
        origin_x=cfg.get("CHESS_ORIGIN_X_MM", 0.0),
        origin_y=cfg.get("CHESS_ORIGIN_Y_MM", 0.0),
        tap_dwell_s=cfg.get("CHESS_TAP_DWELL_S", 0.3),
    )
    if config.PLOTTER_DRY_RUN:
        return {"success": True, "dry_run": True, "stats": stats}
    try:
        controller = PlotterController(
            port=config.SERIAL_PORT,
            baudrate=config.SERIAL_BAUDRATE,
            timeout=getattr(config, "SERIAL_TIMEOUT", 10.0),
            line_delay=config.PLOTTER_LINE_DELAY,
        )
        controller.connect()
        try:
            controller.send_gcode_lines(gcode_lines)
        finally:
            controller.disconnect()
        return {"success": True, "stats": stats}
    except PlotterError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Chess demo run failed: %s", e)
        raise HTTPException(status_code=500, detail="Unexpected error during demo.")


# --- Chess play ---


@router.post("/chess/play/setup")
def chess_play_setup(body: dict | None = Body(default=None)):
    body = body or {}
    mode = body.get("mode", "human_v_human")
    difficulty = body.get("difficulty")
    sess = get_session()
    sess.set_mode(mode)
    if difficulty is not None:
        sess.set_difficulty(difficulty)
    sess.reset()
    return {"mode": sess.mode, "difficulty": sess.get_difficulty(), "fen": sess.get_fen()}


@router.get("/chess/play/status")
def chess_play_status():
    sess = get_session()
    return {
        "fen": sess.get_fen(),
        "mode": sess.mode,
        "difficulty": sess.get_difficulty(),
        "turn": "white" if sess.is_white_turn() else "black",
        "game_over": sess.is_game_over(),
        "result": sess.result(),
    }


@router.post("/chess/execute-move")
def chess_execute_move(request: Request, body: dict | None = Body(default=None)):
    """Stateless endpoint: send a single UCI move to the plotter. Used by Neo_Chess."""
    body = body or {}
    uci = (body.get("uci") or "").strip()
    capture = body.get("capture", False)
    if len(uci) < 4:
        raise HTTPException(status_code=400, detail="Provide valid UCI move (e.g. e2e4)")
    try:
        _send_move_gcode(uci, capture, request)
    except Exception as e:
        logger.exception("Execute move failed: %s", e)
        raise HTTPException(status_code=500, detail="Execute failed: " + str(e))
    return {"success": True, "dry_run": get_config().PLOTTER_DRY_RUN}


def _send_move_gcode(uci: str, capture: bool, request: Request) -> None:
    cfg = _config_dict(request)
    board_mm = cfg.get("CHESS_BOARD_SIZE_MM", 200.0)
    square_count = cfg.get("CHESS_SQUARE_COUNT", 8)
    origin_x = cfg.get("CHESS_ORIGIN_X_MM", 0.0)
    origin_y = cfg.get("CHESS_ORIGIN_Y_MM", 0.0)
    config = get_config()
    if getattr(config, "CHESS_MAGNET_MAX_ON_S", None) is not None and len(uci) >= 4:
        fx, fy = uci_square_to_mm(uci[0], uci[1], board_mm, square_count, origin_x, origin_y)
        tx, ty = uci_square_to_mm(uci[2], uci[3], board_mm, square_count, origin_x, origin_y)
        distance_mm = math.sqrt((tx - fx) ** 2 + (ty - fy) ** 2)
        rapid_mm_s = getattr(config, "CHESS_RAPID_FEED_MM_S", 100.0)
        move_time_s = distance_mm / rapid_mm_s if rapid_mm_s > 0 else 0.0
        if move_time_s > config.CHESS_MAGNET_MAX_ON_S:
            logger.warning(
                "Move %s distance %.0f mm (~%.2f s) exceeds CHESS_MAGNET_MAX_ON_S=%.2f s",
                uci,
                distance_mm,
                move_time_s,
                config.CHESS_MAGNET_MAX_ON_S,
            )
    lines = move_to_gcode(
        uci,
        capture,
        board_size_mm=board_mm,
        square_count=square_count,
        origin_x=origin_x,
        origin_y=origin_y,
        discard_offset_squares=cfg.get("CHESS_DISCARD_OFFSET_SQUARES", 1.5),
        dwell_s=cfg.get("CHESS_TAP_DWELL_S", 0.3),
        settle_after_place_s=cfg.get("CHESS_MAGNET_SETTLE_S", 0.5),
    )
    if cfg.get("PLOTTER_DRY_RUN"):
        return
    config = get_config()
    controller = PlotterController(
        port=config.SERIAL_PORT,
        baudrate=config.SERIAL_BAUDRATE,
        timeout=getattr(config, "SERIAL_TIMEOUT", 10.0),
        line_delay=config.PLOTTER_LINE_DELAY,
    )
    controller.connect()
    try:
        controller.send_gcode_lines(lines)
    finally:
        controller.disconnect()


@router.post("/chess/play/move")
def chess_play_move(request: Request, body: dict | None = Body(default=None)):
    body = body or {}
    uci = (body.get("uci") or "").strip()
    step = body.get("step", False)
    execute = body.get("execute", False)
    sess = get_session()
    moves_with_capture: list[tuple[str, bool]] = []

    if step and sess.mode == "computer_v_computer":
        ai = sess.get_ai_move()
        if ai:
            moves_with_capture.append((ai, False))
    elif uci:
        capture = sess.is_capture(uci)
        if not sess.play_move(uci):
            raise HTTPException(status_code=400, detail="Illegal move")
        moves_with_capture.append((uci, capture))
        if sess.mode == "human_v_computer" and not sess.is_game_over():
            ai = sess.get_ai_move()
            if ai:
                moves_with_capture.append((ai, False))
    else:
        raise HTTPException(status_code=400, detail="Provide uci or step")

    moves_done = [m for m, _ in moves_with_capture]
    if execute and moves_done:
        try:
            b = sess.board.copy()
            for i in range(len(moves_done) - 1, -1, -1):
                b.pop()
            for m in moves_done:
                cap = b.is_capture(chess.Move.from_uci(m))
                _send_move_gcode(m, cap, request)
                b.push(chess.Move.from_uci(m))
        except Exception as e:
            logger.exception("Chess play execute failed: %s", e)
            raise HTTPException(status_code=500, detail="Execute failed: " + str(e))

    return {
        "fen": sess.get_fen(),
        "moves": moves_done,
        "turn": "white" if sess.is_white_turn() else "black",
        "game_over": sess.is_game_over(),
        "result": sess.result(),
    }
