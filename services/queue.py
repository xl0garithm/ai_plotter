"""Job queue management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from flask import current_app
from werkzeug.datastructures import FileStorage

from config import Config
from models import Job
from services.database import session_scope
from services.gemini_client import GeminiClient, GeminiClientError
from services import gcode as gcode_service
from services import image_processing
from services.plotter import PlotterController, PlotterError


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


def _get_queue_config(config: Union[Config, Dict[str, Any]]) -> QueueConfig:
    if isinstance(config, dict):
        upload_dir = Path(config["UPLOAD_DIR"])
        generated_dir = Path(config["GENERATED_DIR"])
        gcode_dir = Path(config["GCODE_DIR"])
    else:
        upload_dir = Path(config.UPLOAD_DIR)
        generated_dir = Path(config.GENERATED_DIR)
        gcode_dir = Path(config.GCODE_DIR)
    return QueueConfig(upload_dir=upload_dir, generated_dir=generated_dir, gcode_dir=gcode_dir)


def _logger():
    try:
        return current_app.logger
    except RuntimeError:
        return logging.getLogger("services.queue")


def _is_dry_run(config: Union[Config, Dict[str, Any]]) -> bool:
    if isinstance(config, dict):
        value = config.get("PLOTTER_DRY_RUN")
    else:
        value = getattr(config, "PLOTTER_DRY_RUN", False)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _is_z_inverted(config: Union[Config, Dict[str, Any]]) -> bool:
    if isinstance(config, dict):
        value = config.get("PLOTTER_INVERT_Z")
    else:
        value = getattr(config, "PLOTTER_INVERT_Z", False)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _touch_job(session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise QueueError(f"Job {job_id} not found.")
    job.updated_at = datetime.utcnow()
    return job


def _job_to_public_dict(job: Job) -> Dict[str, Any]:
    return job.to_dict(admin=False)


def _job_to_admin_dict(job: Job) -> Dict[str, Any]:
    return job.to_dict(admin=True)


def create_job_from_upload(
    upload: FileStorage,
    *,
    prompt: Optional[str],
    requester: Optional[str],
    config: Config,
    gemini_client: GeminiClient,
) -> Dict[str, Any]:
    """Create a new job from an uploaded image and trigger generation."""
    if upload is None or upload.filename == "":
        raise QueueError("No image provided.")

    cfg = _get_queue_config(config)
    asset_key = image_processing.generate_asset_key()
    original_path = cfg.upload_dir / f"{asset_key}_original.png"

    image_processing.save_upload(upload, original_path)

    with session_scope() as session:
        job = Job(
            asset_key=asset_key,
            status=JobStatus.SUBMITTED.value,
            requester=requester,
            prompt=prompt,
            original_path=str(original_path),
        )
        session.add(job)
        session.flush()
        job_id = job.id

    try:
        _generate_caricature(job_id, gemini_client, cfg, prompt)
    except GeminiClientError as exc:
        _logger().exception("Gemini generation failed for job %s: %s", job_id, exc)
        mark_job_failed(job_id, str(exc))
        raise
    except Exception as exc:  # noqa: BLE001
        _logger().exception("Job generation failed for job %s: %s", job_id, exc)
        mark_job_failed(job_id, str(exc))
        raise

    return get_job(job_id, admin=False)


def create_job_from_manual_upload(
    upload: FileStorage,
    *,
    requester: Optional[str],
    config: Config,
) -> Dict[str, Any]:
    """Create a job directly from an uploaded outline image."""
    if upload is None or upload.filename == "":
        raise QueueError("No image provided.")

    cfg = _get_queue_config(config)
    asset_key = image_processing.generate_asset_key()
    original_path = cfg.upload_dir / f"{asset_key}_manual.png"
    generated_path = cfg.generated_dir / f"{asset_key}_manual_generated.png"

    image_processing.save_upload(upload, original_path)
    resized = image_processing.resize_image_bytes(original_path.read_bytes(), (400, 400))
    image_processing.save_image_bytes(resized, generated_path)

    with session_scope() as session:
        job = Job(
            asset_key=asset_key,
            status=JobStatus.GENERATED.value,
            requester=requester,
            prompt="Manual admin upload",
            original_path=str(original_path),
            generated_path=str(generated_path),
        )
        session.add(job)
        session.flush()
        job_id = job.id

    return get_job(job_id, admin=True)


def _generate_caricature(job_id: int, gemini_client: GeminiClient, cfg: QueueConfig, prompt: Optional[str]) -> None:
    """Invoke Gemini to generate a caricature for the job."""
    set_job_status(job_id, JobStatus.GENERATING)

    with session_scope() as session:
        job = _touch_job(session, job_id)
        original_path = Path(job.original_path)
        asset_key = job.asset_key
        if not original_path.exists():
            raise QueueError("Original image not found on disk.")
        image_bytes = original_path.read_bytes()

    generated_bytes = gemini_client.generate_caricature(image_bytes, prompt)
    resized_bytes = image_processing.resize_image_bytes(generated_bytes, (400, 400))
    generated_path = cfg.generated_dir / f"{asset_key}_generated.png"
    image_processing.save_image_bytes(resized_bytes, generated_path)

    with session_scope() as session:
        job = _touch_job(session, job_id)
        job.generated_path = str(generated_path)
        job.status = JobStatus.GENERATED.value
        job.error_message = None


def get_job(job_id: int, *, admin: bool = False) -> Dict[str, Any]:
    """Return a single job."""
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise QueueError(f"Job {job_id} not found.")
        return job.to_dict(admin=admin)


def list_jobs(*, admin: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
    """Return jobs for display."""
    with session_scope() as session:
        query = session.query(Job).order_by(Job.created_at.desc()).limit(limit)
        jobs: Iterable[Job] = query.all()
        if admin:
            return [_job_to_admin_dict(job) for job in jobs]
        return [_job_to_public_dict(job) for job in jobs]


def set_job_status(job_id: int, status: JobStatus) -> Dict[str, Any]:
    """Update job status."""
    with session_scope() as session:
        job = _touch_job(session, job_id)
        job.status = status.value
        if status == JobStatus.CONFIRMED:
            job.confirmed_at = datetime.utcnow()
        elif status == JobStatus.APPROVED:
            job.approved_at = datetime.utcnow()
        elif status == JobStatus.PRINTING:
            job.started_at = datetime.utcnow()
        elif status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()
        return job.to_dict(admin=True)


def confirm_job(job_id: int) -> Dict[str, Any]:
    """Mark a job as confirmed by a user."""
    job = get_job(job_id, admin=True)
    if job["status"] != JobStatus.GENERATED.value:
        raise QueueError("Job cannot be confirmed in its current state.")
    return set_job_status(job_id, JobStatus.CONFIRMED)


def approve_job(job_id: int) -> Dict[str, Any]:
    """Approve a job for plotting."""
    job = get_job(job_id, admin=True)
    if job["status"] not in (JobStatus.CONFIRMED.value, JobStatus.GENERATED.value):
        raise QueueError("Only generated or confirmed jobs can be approved.")
    return set_job_status(job_id, JobStatus.APPROVED)


def queue_for_printing(job_id: int, config: Union[Config, Dict[str, Any]]) -> Dict[str, Any]:
    """Move job to queued state for plotting."""
    job = get_job(job_id, admin=True)
    if job["status"] not in (JobStatus.APPROVED.value, JobStatus.CONFIRMED.value):
        raise QueueError("Job must be approved or confirmed before queuing.")

    cfg = _get_queue_config(config)

    with session_scope() as session:
        obj = _touch_job(session, job_id)
        if not obj.generated_path:
            raise QueueError("Generated image not available for G-code conversion.")
        generated_path = Path(obj.generated_path)
        if not generated_path.exists():
            raise QueueError("Generated image file missing.")
        gcode_path = Path(obj.gcode_path) if obj.gcode_path else cfg.gcode_dir / f"{obj.asset_key}.gcode"

    try:
        # Custom settings optimized for quality and speed
        settings = gcode_service.GCodeSettings(
            pixel_size_mm=0.25,  # Good balance of size and quality
            feed_rate=8000,  # Very fast drawing speed
            travel_height=5.0,
            draw_height=0.0,
            invert_z=_is_z_inverted(config),
            threshold=250,  # Higher threshold for cleaner lines
            blur_radius=0.3,  # Even less blurring for sharper lines
            thinning_iterations=8,  # Even fewer iterations to preserve detail
            point_skip=1,  # No point skipping for better quality
            min_move_mm=0.05,  # Much smaller minimum moves for finer detail
            pen_dwell_seconds=0.05,  # Shorter dwell time
        )
        gcode_service.image_to_gcode(generated_path, gcode_path, settings=settings)
    except gcode_service.GCodeError as exc:
        _logger().exception("Failed to convert image to G-code for job %s: %s", job_id, exc)
        mark_job_failed(job_id, str(exc))
        raise

    with session_scope() as session:
        obj = _touch_job(session, job_id)
        obj.gcode_path = str(gcode_path)
        obj.status = JobStatus.QUEUED.value
        obj.error_message = None

    return get_job(job_id, admin=True)


def start_print_job(
    job_id: int,
    config: Union[Config, Dict[str, Any]],
    *,
    allow_reprint: bool = False,
) -> Dict[str, Any]:
    """Send the job's G-code to the plotter."""
    job = get_job(job_id, admin=True)
    status = job["status"]
    allowed_statuses = {
        JobStatus.QUEUED.value,
        JobStatus.APPROVED.value,
        JobStatus.CONFIRMED.value,
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

    if _is_dry_run(config):
        _logger().info("Dry-run enabled; writing G-code to text file for job %s", job_id)
        set_job_status(job_id, JobStatus.PRINTING)
        gcode_file = Path(gcode_path)
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

        try:
            controller.connect()
            set_job_status(job_id, JobStatus.PRINTING)
            controller.send_gcode_file(Path(gcode_path))
        except PlotterError as exc:
            _logger().exception("Plotter error while printing job %s: %s", job_id, exc)
            mark_job_failed(job_id, str(exc))
            raise
        finally:
            controller.disconnect()
            _plotter_state.controller = None

    return set_job_status(job_id, JobStatus.COMPLETED)


def cancel_job(job_id: int) -> Dict[str, Any]:
    """Cancel a job."""
    job = get_job(job_id, admin=True)
    if job["status"] in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
        return job
    set_job_status(job_id, JobStatus.CANCELLED)
    _signal_plotter_cancel()
    return get_job(job_id, admin=True)


def _signal_plotter_cancel() -> None:
    """Trigger cancellation on any active plotter controller."""
    controller = getattr(_plotter_state, "controller", None)
    if controller:
        controller.request_cancel()


class _PlotterState:
    controller: Optional[PlotterController] = None


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

