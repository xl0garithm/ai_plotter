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
    admin_job = queue.get_job(job["id"], admin=True)
    generated_path = Path(admin_job["generated_path"])
    assert generated_path.exists()
    assert generated_path.name.startswith(f"{job['id']}-")
    assert generated_path.suffix == ".png"

    job = queue.confirm_job(job["id"])

    sent_lines = []

    class DummyPlotter:
        def __init__(self, *args, **kwargs):
            self.connected = False
            self.rehome_called = False

        def connect(self):
            self.connected = True

        def disconnect(self):
            self.connected = False

        def rehome(self):
            self.rehome_called = True

        def send_gcode_lines(self, lines, *, progress_callback=None):
            for idx, line in enumerate(lines, start=1):
                sent_lines.append(line)
                if progress_callback:
                    progress_callback(idx)

    monkeypatch.setattr(queue, "PlotterController", DummyPlotter)

    job = queue.start_print_job(job["id"], config)

    assert job["status"] == queue.JobStatus.COMPLETED.value
    assert sent_lines, "G-code should be streamed to plotter"
    stored_gcode = Path(queue.get_job(job["id"], admin=True)["gcode_path"])
    assert stored_gcode.exists()
    assert stored_gcode.name.startswith(f"{job['id']}-")
    assert stored_gcode.suffix == ".gcode"
    assert "G1 X" in stored_gcode.read_text(encoding="utf-8")


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
    result = queue.start_print_job(job["id"], config)

    assert result["status"] == queue.JobStatus.COMPLETED.value
    gcode_path = Path(queue.get_job(job["id"], admin=True)["gcode_path"])
    assert gcode_path.name.startswith(f"{job['id']}-")
    assert gcode_path.suffix == ".gcode"
    dry_run_path = gcode_path.with_suffix(".dryrun.txt")
    assert dry_run_path.exists()
    assert dry_run_path.read_text(encoding="utf-8") == gcode_path.read_text(encoding="utf-8")
    assert "G1 X" in gcode_path.read_text(encoding="utf-8")


def test_print_job_rehomes_when_flagged(monkeypatch, test_storage, sample_upload):
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
        prompt="Rehome test",
        requester="tester",
        config=config,
        gemini_client=StubGemini(),
    )
    queue.confirm_job(job["id"])

    class RehomePlotter:
        instances = []

        def __init__(self, *args, **kwargs):
            self.connected = False
            self.rehome_called = False
            RehomePlotter.instances.append(self)

        def connect(self):
            self.connected = True

        def disconnect(self):
            self.connected = False

        def rehome(self):
            self.rehome_called = True

        def send_gcode_lines(self, lines, *, progress_callback=None):
            for idx, _ in enumerate(lines, start=1):
                if progress_callback:
                    progress_callback(idx)
            # simulate an external cancel request flag
            queue._plotter_state.should_rehome_on_cancel = True

    monkeypatch.setattr(queue, "PlotterController", RehomePlotter)

    result = queue.start_print_job(job["id"], config)

    assert result["status"] == queue.JobStatus.COMPLETED.value
    assert RehomePlotter.instances, "Plotter should be instantiated"
    assert RehomePlotter.instances[-1].rehome_called is True
    assert queue._plotter_state.should_rehome_on_cancel is False


def test_accepts_arbitrary_contact_text(test_storage, sample_upload):
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

    freestyle = "Ping me on Threads @plotfan"
    job = queue.create_job_from_upload(
        upload,
        prompt=None,
        requester="tester",
        email=freestyle,
        config=config,
        gemini_client=StubGemini(),
    )

    admin_job = queue.get_job(job["id"], admin=True)
    assert admin_job["email"] == freestyle


def test_sanitizes_control_characters_in_email(test_storage, sample_upload):
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

    noisy = "  alert\x00('hi')\n "
    job = queue.create_job_from_upload(
        upload,
        prompt=None,
        requester="tester",
        email=noisy,
        config=config,
        gemini_client=StubGemini(),
    )
    stored_email = queue.get_job(job["id"], admin=True)["email"]
    assert stored_email == "alert('hi')"
