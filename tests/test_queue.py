from pathlib import Path

import pytest

from services import queue


class StubGemini:
    def generate_caricature(self, image_bytes: bytes, prompt=None) -> bytes:
        return image_bytes


def test_job_lifecycle(monkeypatch, test_storage, sample_upload):
    upload = sample_upload()
    config = {
        "UPLOAD_DIR": test_storage["UPLOAD_DIR"],
        "GENERATED_DIR": test_storage["GENERATED_DIR"],
        "GCODE_DIR": test_storage["GCODE_DIR"],
        "SERIAL_PORT": test_storage["SERIAL_PORT"],
        "SERIAL_BAUDRATE": test_storage["SERIAL_BAUDRATE"],
        "PLOTTER_DRY_RUN": False,
        "PLOTTER_INVERT_Z": False,
    }

    job = queue.create_job_from_upload(
        upload,
        prompt=None,
        requester="tester",
        config=config,
        gemini_client=StubGemini(),
    )

    assert job["status"] == queue.JobStatus.GENERATED.value
    generated_path = Path(queue.get_job(job["id"], admin=True)["generated_path"])
    assert generated_path.exists()

    job = queue.approve_job(job["id"])

    sent_paths = []

    class DummyPlotter:
        def __init__(self, *args, **kwargs):
            self.connected = False

        def connect(self):
            self.connected = True

        def disconnect(self):
            self.connected = False

        def send_gcode_file(self, path: Path):
            sent_paths.append(Path(path))

    monkeypatch.setattr(queue, "PlotterController", DummyPlotter)

    job = queue.start_print_job(job["id"], config)

    assert job["status"] == queue.JobStatus.COMPLETED.value
    assert sent_paths, "G-code should be sent to plotter"
    assert sent_paths[0].exists()
    assert "G1 X" in sent_paths[0].read_text(encoding="utf-8")
    stored_gcode = Path(queue.get_job(job["id"], admin=True)["gcode_path"])
    assert stored_gcode == sent_paths[0]


def test_start_print_job_dry_run(test_storage, sample_upload):
    upload = sample_upload()
    config = {
        "UPLOAD_DIR": test_storage["UPLOAD_DIR"],
        "GENERATED_DIR": test_storage["GENERATED_DIR"],
        "GCODE_DIR": test_storage["GCODE_DIR"],
        "SERIAL_PORT": test_storage["SERIAL_PORT"],
        "SERIAL_BAUDRATE": test_storage["SERIAL_BAUDRATE"],
        "PLOTTER_DRY_RUN": True,
        "PLOTTER_INVERT_Z": False,
    }

    job = queue.create_job_from_upload(
        upload,
        prompt="Dry run test",
        requester="tester",
        config=config,
        gemini_client=StubGemini(),
    )
    queue.approve_job(job["id"])

    result = queue.start_print_job(job["id"], config)

    assert result["status"] == queue.JobStatus.COMPLETED.value
    gcode_path = Path(queue.get_job(job["id"], admin=True)["gcode_path"])
    dry_run_path = gcode_path.with_suffix(".dryrun.txt")
    assert dry_run_path.exists()
    assert dry_run_path.read_text(encoding="utf-8") == gcode_path.read_text(encoding="utf-8")
    assert "G1 X" in gcode_path.read_text(encoding="utf-8")

