import io
import pytest
from PIL import Image, ImageDraw
from werkzeug.datastructures import FileStorage

from services.database import init_db


@pytest.fixture(scope="session")
def test_storage(tmp_path_factory):
    base = tmp_path_factory.mktemp("storage")
    upload = base / "uploads"
    generated = base / "processed"
    gcode = base / "gcode"
    for path in (upload, generated, gcode):
        path.mkdir(parents=True, exist_ok=True)

    db_path = base / "test.db"
    init_db(f"sqlite:///{db_path}")

    return {
        "STORAGE_DIR": base,
        "UPLOAD_DIR": upload,
        "GENERATED_DIR": generated,
        "GCODE_DIR": gcode,
        "SERIAL_PORT": "loop://",
        "SERIAL_BAUDRATE": 115200,
    }


@pytest.fixture
def sample_upload():
    def factory():
        image = Image.new("RGB", (400, 400), color="white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((60, 60, 340, 340), outline="black", width=6)
        draw.ellipse((150, 150, 250, 250), outline="black", width=4)
        draw.line((80, 300, 320, 120), fill="black", width=3)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        data = buffer.getvalue()
        return FileStorage(
            stream=io.BytesIO(data),
            filename="capture.png",
            content_type="image/png",
        )

    return factory

