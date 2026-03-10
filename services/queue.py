"""Job queue management."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage

from config import Config
from models import Job
from services import gcode as gcode_service
from services import image_processing, vectorizer
from services.database import session_scope
from services.plotter import PlotterController, PlotterError
from services.style_presets import DEFAULT_STYLE_KEY, get_style


class QueueError(RuntimeError):
    """Raised when queue operations fail."""


class JobStatus(str, Enum):
    SUBMITTED = "submitted"
    GENERATING = "generating"
    GENERATED = "generated"
    CONFIRMED = "confirmed"
    APPROVED = "approved"
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueConfig:
    """DTO for queue configuration values."""

    upload_dir: Path
    generated_dir: Path
    gcode_dir: Path


def _get_queue_config(config: Config | dict[str, Any]) -> QueueConfig:
    if isinstance(config, dict):
        upload_dir = Path(config["UPLOAD_DIR"])
        generated_dir = Path(config["GENERATED_DIR"])
        gcode_dir = Path(config["GCODE_DIR"])
    else:
        upload_dir = Path(config.UPLOAD_DIR)
        generated_dir = Path(config.GENERATED_DIR)
        gcode_dir = Path(config.GCODE_DIR)
    return QueueConfig(upload_dir=upload_dir, generated_dir=generated_dir, gcode_dir=gcode_dir)


def _config_value(config: Config | dict[str, Any], name: str, default: Any) -> Any:
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


logger = logging.getLogger(__name__)


def _temporary_asset_key() -> str:
    """Return a unique placeholder asset key before a job ID exists."""
    return f"pending-{uuid.uuid4().hex}"


def _is_dry_run(config: Config | dict[str, Any]) -> bool:
    if isinstance(config, dict):
        value = config.get("PLOTTER_DRY_RUN")
    else:
        value = getattr(config, "PLOTTER_DRY_RUN", False)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _is_z_inverted(config: Config | dict[str, Any]) -> bool:
    if isinstance(config, dict):
        value = config.get("PLOTTER_INVERT_Z")
    else:
        value = getattr(config, "PLOTTER_INVERT_Z", False)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _vectorize_and_store(
    asset_key: str,
    image_path: Path,
    cfg: QueueConfig,
    config: Config | dict[str, Any],
) -> dict[str, Any]:
    """Run vectorization and persist SVG/JSON artifacts."""

    threshold = int(_config_value(config, "VECTORIZE_THRESHOLD", 240))
    simplify = float(_config_value(config, "VECTORIZE_SIMPLIFY_PX", 2.0))
    min_points = int(_config_value(config, "VECTORIZE_MIN_POINTS", 24))
    downsample_step = int(_config_value(config, "VECTORIZE_DOWNSAMPLE_STEP", 1))
    stroke_px = float(_config_value(config, "VECTORIZE_STROKE_WIDTH", 3.0))
    crop_padding_ratio = float(_config_value(config, "VECTORIZE_CROP_PADDING_RATIO", 0.05))
    resolution = int(_config_value(config, "VECTOR_RESOLUTION", 1600))

    vector_data = vectorizer.vectorize_image(
        image_path,
        threshold=threshold,
        simplify_tolerance=simplify,
        min_path_points=min_points,
        downsample_step=downsample_step,
    )
    vector_data = vectorizer.crop_and_scale_vector_data(
        vector_data,
        padding_ratio=crop_padding_ratio,
        target_dimension=resolution,
    )

    vector_json = cfg.generated_dir / f"{asset_key}.json"
    vector_svg = cfg.generated_dir / f"{asset_key}.svg"
    vectorizer.save_vector_data(vector_data, vector_json)
    vectorizer.save_svg(vector_data, vector_svg, stroke_px=stroke_px)

    return {
        "vector_data_path": str(vector_json),
        "vector_svg_path": str(vector_svg),
        "vector_width": vector_data.width,
        "vector_height": vector_data.height,
    }


def _touch_job(session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise QueueError(f"Job {job_id} not found.")
    job.updated_at = datetime.now(timezone.utc)
    return job


def _init_print_progress(job_id: int, total_lines: int) -> None:
    total_lines = max(0, int(total_lines))
    with session_scope() as session:
        obj = _touch_job(session, job_id)
        metadata = obj.metadata_json or {}
        metadata["print_progress"] = {
            "total_lines": total_lines,
            "current_line": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        obj.metadata_json = metadata


def _update_print_progress(
    job_id: int,
    *,
    current_line: int,
    total_lines: int | None = None,
) -> None:
    with session_scope() as session:
        obj = _touch_job(session, job_id)
        metadata = obj.metadata_json or {}
        progress = metadata.get("print_progress") or {}
        if total_lines is not None:
            progress["total_lines"] = max(0, int(total_lines))
        existing_total = progress.get("total_lines") or total_lines or 0
        safe_current = max(
            0, min(int(current_line), int(existing_total) if existing_total else int(current_line))
        )
        progress.update(
            {
                "current_line": safe_current,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        metadata["print_progress"] = progress
        obj.metadata_json = metadata


def _clear_print_progress(job_id: int) -> None:
    with session_scope() as session:
        obj = _touch_job(session, job_id)
        metadata = obj.metadata_json or {}
        if "print_progress" in metadata:
            metadata.pop("print_progress", None)
            obj.metadata_json = metadata


def create_job_from_manual_upload(
    upload: FileStorage | tuple,
    *,
    requester: str | None,
    config: Config,
) -> dict[str, Any]:
    """Create a job directly from an uploaded outline image. upload is FileStorage or (bytes, filename)."""
    if upload is None:
        raise QueueError("No image provided.")
    if isinstance(upload, tuple):
        content, filename = upload
        if not content or not filename:
            raise QueueError("No image provided.")
    else:
        if upload.filename == "":
            raise QueueError("No image provided.")

    cfg = _get_queue_config(config)
    style = get_style(DEFAULT_STYLE_KEY)
    placeholder_key = _temporary_asset_key()
    resolution = int(_config_value(config, "VECTOR_RESOLUTION", 1600))

    with session_scope() as session:
        job = Job(
            asset_key=placeholder_key,
            status=JobStatus.GENERATED.value,
            requester=requester,
            prompt="Manual admin upload",
            original_path="",
            generated_path="",
            metadata_json=None,
        )
        session.add(job)
        session.flush()
        job_id = job.id
        asset_key = image_processing.generate_asset_key(job_id)
        original_path = cfg.upload_dir / f"{asset_key}.png"
        generated_path = cfg.generated_dir / f"{asset_key}.png"
        if isinstance(upload, tuple):
            content, _ = upload
            original_path.parent.mkdir(parents=True, exist_ok=True)
            original_path.write_bytes(content)
        else:
            image_processing.save_upload(upload, original_path)
        resized = image_processing.resize_image_bytes(
            original_path.read_bytes(), (resolution, resolution)
        )
        image_processing.save_image_bytes(resized, generated_path)
        vector_meta = _vectorize_and_store(asset_key, generated_path, cfg, config)
        metadata = {
            "style_key": DEFAULT_STYLE_KEY,
            "style_label": style["label"],
            "style_description": style["description"],
            "style_prompt": style["prompt"],
            **vector_meta,
        }
        job.asset_key = asset_key
        job.original_path = str(original_path)
        job.generated_path = str(generated_path)
        job.metadata_json = metadata

    return get_job(job_id, admin=True)


def get_job(job_id: int, *, admin: bool = False) -> dict[str, Any]:
    """Return a single job."""
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise QueueError(f"Job {job_id} not found.")
        return job.to_dict(admin=admin)


def list_jobs(*, admin: bool = False, limit: int = 20) -> list[dict[str, Any]]:
    """Return jobs for display."""
    with session_scope() as session:
        query = session.query(Job).order_by(Job.created_at.desc()).limit(limit)
        jobs: Iterable[Job] = query.all()
        if admin:
            return [job.to_dict(admin=True) for job in jobs]
        return [job.to_dict(admin=False) for job in jobs]


def set_job_status(job_id: int, status: JobStatus) -> dict[str, Any]:
    """Update job status."""
    with session_scope() as session:
        job = _touch_job(session, job_id)
        job.status = status.value
        if status == JobStatus.CONFIRMED:
            job.confirmed_at = datetime.now(timezone.utc)
        elif status == JobStatus.APPROVED:
            job.approved_at = datetime.now(timezone.utc)
        elif status == JobStatus.PRINTING:
            job.started_at = datetime.now(timezone.utc)
        elif status == JobStatus.COMPLETED:
            job.completed_at = datetime.now(timezone.utc)
        return job.to_dict(admin=True)


def confirm_job(job_id: int) -> dict[str, Any]:
    """Mark a job as confirmed by a user."""
    job = get_job(job_id, admin=True)
    if job["status"] != JobStatus.GENERATED.value:
        raise QueueError("Job cannot be confirmed in its current state.")
    return set_job_status(job_id, JobStatus.CONFIRMED)


def approve_job(job_id: int) -> dict[str, Any]:
    """Approve a job for plotting."""
    job = get_job(job_id, admin=True)
    if job["status"] not in (JobStatus.CONFIRMED.value, JobStatus.GENERATED.value):
        raise QueueError("Only generated or confirmed jobs can be approved.")
    return set_job_status(job_id, JobStatus.APPROVED)


def queue_for_printing(job_id: int, config: Config | dict[str, Any]) -> dict[str, Any]:
    """Move job to queued state for plotting."""
    job = get_job(job_id, admin=True)
    allowed_statuses = {
        JobStatus.APPROVED.value,
        JobStatus.CONFIRMED.value,
        JobStatus.GENERATED.value,
    }
    if job["status"] not in allowed_statuses:
        raise QueueError("Job must be generated or confirmed before queuing.")
    if job["status"] == JobStatus.GENERATED.value:
        job = set_job_status(job_id, JobStatus.CONFIRMED)

    cfg = _get_queue_config(config)

    metadata: dict[str, Any] = {}
    with session_scope() as session:
        obj = _touch_job(session, job_id)
        if not obj.generated_path:
            raise QueueError("Generated image not available for G-code conversion.")
        generated_path = Path(obj.generated_path)
        if not generated_path.exists():
            raise QueueError("Generated image file missing.")
        gcode_path = (
            Path(obj.gcode_path) if obj.gcode_path else cfg.gcode_dir / f"{obj.asset_key}.gcode"
        )
        metadata = obj.metadata_json or {}

        vector_data: vectorizer.VectorData | None = None
        vector_data_path = metadata.get("vector_data_path")
        candidate_paths = []
        if vector_data_path:
            candidate_paths.append(Path(vector_data_path))
        candidate_paths.append(cfg.generated_dir / f"{obj.asset_key}.json")
        candidate_paths.append(cfg.generated_dir / f"{obj.asset_key}_vector.json")

        for candidate in candidate_paths:
            if candidate.exists():
                vector_data = vectorizer.load_vector_data(candidate)
                svg_candidate = cfg.generated_dir / f"{obj.asset_key}.svg"
                legacy_svg_candidate = cfg.generated_dir / f"{obj.asset_key}_vector.svg"
                if not svg_candidate.exists() and legacy_svg_candidate.exists():
                    svg_path_for_meta = legacy_svg_candidate
                else:
                    svg_path_for_meta = svg_candidate
                metadata = {
                    **metadata,
                    "vector_data_path": str(candidate),
                    "vector_svg_path": str(svg_path_for_meta),
                }
                obj.metadata_json = metadata
                break

        if not vector_data:
            raise QueueError("Vector data missing for job; add generated image before queuing.")

    try:
        target_size_mm = 100.0  # physical drawing size
        configured_resolution = int(_config_value(config, "VECTOR_RESOLUTION", 1600))
        effective_resolution = max(
            configured_resolution,
            max(vector_data.width, vector_data.height) if vector_data else 0,
        )
        pixel_size_mm = target_size_mm / max(effective_resolution, 1)
        default_settings = gcode_service.GCodeSettings()
        feed_rate = int(_config_value(config, "PLOTTER_FEED_RATE", default_settings.feed_rate))

        settings = gcode_service.GCodeSettings(
            pixel_size_mm=pixel_size_mm,
            feed_rate=feed_rate,
            travel_height=5.0,
            draw_height=0.0,
            invert_z=_is_z_inverted(config),
            min_move_mm=0.1,
            pen_dwell_seconds=0.05,
        )

        gcode_stats = gcode_service.vector_data_to_gcode(vector_data, gcode_path, settings=settings)
    except gcode_service.GCodeError as exc:
        logger.exception("Failed to convert image to G-code for job %s: %s", job_id, exc)
        mark_job_failed(job_id, str(exc))
        raise

    metadata = {
        **(metadata or {}),
        "estimated_print_seconds": round(gcode_stats.estimated_seconds, 2),
        "gcode_stats": {
            "total_draw_mm": round(gcode_stats.total_draw_mm, 2),
            "total_travel_mm": round(gcode_stats.total_travel_mm, 2),
            "path_count": gcode_stats.path_count,
            "line_count": gcode_stats.line_count,
        },
    }

    with session_scope() as session:
        obj = _touch_job(session, job_id)
        obj.gcode_path = str(gcode_path)
        obj.status = JobStatus.QUEUED.value
        obj.error_message = None
        obj.metadata_json = metadata

    return get_job(job_id, admin=True)


def start_print_job(
    job_id: int,
    config: Config | dict[str, Any],
    *,
    allow_reprint: bool = False,
) -> dict[str, Any]:
    """Send the job's G-code to the plotter."""
    job = get_job(job_id, admin=True)
    status = job["status"]
    allowed_statuses = {
        JobStatus.QUEUED.value,
        JobStatus.APPROVED.value,
        JobStatus.CONFIRMED.value,
        JobStatus.GENERATED.value,
    }
    if allow_reprint:
        allowed_statuses.update(
            {
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
            }
        )

    if status not in allowed_statuses:
        raise QueueError("Job must be queued or approved before printing.")

    if status != JobStatus.QUEUED.value:
        if allow_reprint and status in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        }:
            with session_scope() as session:
                obj = _touch_job(session, job_id)
                if not obj.gcode_path:
                    raise QueueError("G-code not available for this job.")
                obj.status = JobStatus.QUEUED.value
                obj.error_message = None
            job = get_job(job_id, admin=True)
        else:
            job = queue_for_printing(job_id, config)

    gcode_path = job.get("gcode_path")
    if not gcode_path:
        raise QueueError("G-code not available for this job.")
    gcode_file = Path(gcode_path)

    if _is_dry_run(config):
        logger.info("Dry-run enabled; writing G-code to text file for job %s", job_id)
        set_job_status(job_id, JobStatus.PRINTING)
        dry_run_path = gcode_file.with_suffix(".dryrun.txt")
        dry_run_path.write_text(gcode_file.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        # Access the config object correctly depending on whether it's a dict or object
        if isinstance(config, dict):
            timeout_value = float(config.get("SERIAL_TIMEOUT", 2.0))
            port = config.get("SERIAL_PORT")
            baudrate = int(config.get("SERIAL_BAUDRATE", 115200))
            line_delay = float(config.get("PLOTTER_LINE_DELAY", 0.0))
        else:
            timeout_value = float(getattr(config, "SERIAL_TIMEOUT", 2.0))
            port = getattr(config, "SERIAL_PORT")
            baudrate = int(getattr(config, "SERIAL_BAUDRATE", 115200))
            line_delay = float(getattr(config, "PLOTTER_LINE_DELAY", 0.0))

        controller = PlotterController(
            port=port,
            baudrate=baudrate,
            timeout=timeout_value,
            line_delay=line_delay,
        )
        _plotter_state.controller = controller
        _plotter_state.should_rehome_on_cancel = False

        progress_initialized = False

        try:
            if not gcode_file.exists():
                raise QueueError("G-code file missing on disk.")
            with gcode_file.open("r", encoding="utf-8") as fp:
                gcode_lines = fp.readlines()
            total_lines = len(gcode_lines)
            if total_lines == 0:
                raise QueueError("G-code file is empty.")

            _init_print_progress(job_id, total_lines)
            progress_initialized = True
            min_step = max(1, total_lines // 100)
            last_reported = 0

            def _progress_callback(line_idx: int) -> None:
                nonlocal last_reported
                if line_idx == total_lines or (line_idx - last_reported) >= min_step:
                    _update_print_progress(
                        job_id,
                        current_line=line_idx,
                        total_lines=total_lines,
                    )
                    last_reported = line_idx

            controller.connect()
            set_job_status(job_id, JobStatus.PRINTING)
            controller.send_gcode_lines(
                gcode_lines,
                progress_callback=_progress_callback,
            )
        except PlotterError as exc:
            logger.exception("Plotter error while printing job %s: %s", job_id, exc)
            mark_job_failed(job_id, str(exc))
            raise
        finally:
            try:
                if _plotter_state.should_rehome_on_cancel:
                    controller.rehome()
            except PlotterError as rehome_exc:
                logger.warning(
                    "Failed to rehome after cancellation for job %s: %s", job_id, rehome_exc
                )
            finally:
                controller.disconnect()
            _plotter_state.controller = None
            _plotter_state.should_rehome_on_cancel = False
            if progress_initialized:
                _clear_print_progress(job_id)

    return set_job_status(job_id, JobStatus.COMPLETED)


def cancel_job(job_id: int) -> dict[str, Any]:
    """Cancel a job."""
    job = get_job(job_id, admin=True)
    if job["status"] in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
        return job
    set_job_status(job_id, JobStatus.CANCELLED)
    _signal_plotter_cancel()
    _clear_print_progress(job_id)
    return get_job(job_id, admin=True)


def _signal_plotter_cancel() -> None:
    """Trigger cancellation on any active plotter controller."""
    controller = getattr(_plotter_state, "controller", None)
    if controller:
        _plotter_state.should_rehome_on_cancel = True
        controller.request_cancel()


class _PlotterState:
    controller: PlotterController | None = None
    should_rehome_on_cancel: bool = False


_plotter_state = _PlotterState()


def mark_job_failed(job_id: int, message: str) -> None:
    """Mark job as failed with an error message."""
    with session_scope() as session:
        job = _touch_job(session, job_id)
        job.status = JobStatus.FAILED.value
        job.error_message = message[:512]


def get_generated_image_path(job_id: int) -> Path:
    """Return the path to a job's generated image."""
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise QueueError(f"Job {job_id} not found.")
        if not job.generated_path:
            raise QueueError("Generated image not available.")
        path = Path(job.generated_path)
        if not path.exists():
            raise QueueError("Generated image missing from disk.")
        return path
