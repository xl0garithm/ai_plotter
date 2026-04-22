"""Chess piece-move G-code and electromagnet host directives."""

from __future__ import annotations

import pytest

from app import create_app
from services import plotter as plotter_mod
from services.chess import algebraic_square_to_center_mm, generate_piece_move_gcode
from services.electromagnet import (
    MAGNET_GCODE_OFF,
    MAGNET_GCODE_ON,
    NoOpElectromagnet,
    create_electromagnet,
    parse_magnet_directive,
)
from services.plotter import PlotterController


def test_algebraic_square_to_center_e2():
    x, y = algebraic_square_to_center_mm("e2", 200.0, 8, 0.0, 0.0)
    assert pytest.approx(x, rel=1e-6) == 112.5
    assert pytest.approx(y, rel=1e-6) == 162.5


def test_generate_piece_move_gcode_ordering():
    lines = generate_piece_move_gcode(
        "e2",
        "e4",
        board_size_mm=200.0,
        square_count=8,
        source_settle_s=0.05,
        pickup_dwell_s=0.2,
        place_dwell_s=0.15,
    )
    assert lines[1] == MAGNET_GCODE_OFF
    assert "e2" in lines[2] and lines[2].startswith("G0 ")
    assert lines[3].startswith("G4 ")
    assert lines[4] == MAGNET_GCODE_ON
    assert lines[5].startswith("G4 ")
    assert "e4" in lines[6] and lines[6].startswith("G0 ")
    assert lines[7].startswith("G4 ")
    assert lines[8] == MAGNET_GCODE_OFF


def test_parse_magnet_directive():
    assert parse_magnet_directive("; @MAGNET_ON") == "on"
    assert parse_magnet_directive("  ;  @MAGNET_OFF  ") == "off"
    assert parse_magnet_directive("G0 X0") is None


def test_create_electromagnet_disabled():
    em = create_electromagnet(enabled=False)
    assert isinstance(em, NoOpElectromagnet)


class _FakeSerial:
    """Minimal serial stub: every read returns an ``ok`` line."""

    def __init__(self) -> None:
        self.timeout = 10.0

    @property
    def is_open(self) -> bool:
        return True

    @property
    def in_waiting(self) -> int:
        return 4

    def write(self, data: bytes) -> int:
        return len(data)

    def flush(self) -> None:
        pass

    def read(self, _n: int) -> bytes:
        return b"ok\n"

    def readline(self) -> bytes:
        return b""

    def reset_input_buffer(self) -> None:
        pass

    def reset_output_buffer(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_send_gcode_lines_invokes_electromagnet(monkeypatch):
    def _fake_open(port, baudrate, timeout):
        return _FakeSerial()

    monkeypatch.setattr(plotter_mod, "_open_serial", _fake_open)

    calls: list[str] = []

    class RecordingMag(NoOpElectromagnet):
        def full_on(self) -> None:
            calls.append("on")

        def off(self) -> None:
            calls.append("off")

    ctrl = PlotterController("COM1", 115200, startup_delay=0.0, line_delay=0.0)
    ctrl.connect()
    try:
        ctrl.send_gcode_lines(
            [
                MAGNET_GCODE_OFF,
                "G0 X1 Y1\n",
                MAGNET_GCODE_ON,
                "G0 X2 Y2\n",
                MAGNET_GCODE_OFF,
            ],
            electromagnet=RecordingMag(),
        )
    finally:
        ctrl.disconnect()

    assert calls == ["off", "on", "off"]


@pytest.fixture
def flask_client():
    app = create_app()
    app.config.update(TESTING=True, PLOTTER_DRY_RUN=True)
    with app.test_client() as c:
        yield c


def test_execute_move_dry_run(flask_client):
    rv = flask_client.post("/api/chess/execute-move", json={"from": "e2", "to": "e4"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["success"] is True
    assert data["dry_run"] is True
    assert MAGNET_GCODE_ON in data["gcode_lines"]
    assert any("e2" in ln and ln.startswith("G0") for ln in data["gcode_lines"])
    assert any("e4" in ln and ln.startswith("G0") for ln in data["gcode_lines"])


def test_execute_move_invalid_square(flask_client):
    rv = flask_client.post("/api/chess/execute-move", json={"from": "e9", "to": "e4"})
    assert rv.status_code == 400
