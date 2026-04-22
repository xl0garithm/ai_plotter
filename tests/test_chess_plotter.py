"""Tests for chess UCI → mm mapping and execute-move G-code (README physical assumptions)."""

import pytest

from app import create_app
from services.chess import move_to_gcode, plotter_uci_legs, uci_square_to_mm


@pytest.fixture
def flask_client():
    app = create_app()
    app.config.update(TESTING=True, PLOTTER_DRY_RUN=True)
    with app.test_client() as c:
        yield c


def test_uci_square_to_mm_standard_board_matches_rank_formula():
    board_mm = 200.0
    n = 8
    sq = board_mm / n
    x, y = uci_square_to_mm("e", "4", board_mm, n, 0.0, 0.0)
    assert abs(x - 4.5 * sq) < 1e-6
    assert abs(y - (n + 0.5 - 4) * sq) < 1e-6


def test_uci_square_to_mm_respects_square_count():
    """Non-8 boards must use square_count in Y (regression: was hardcoded 8.5)."""
    board_mm = 100.0
    n = 10
    sq = board_mm / n
    _, y_top = uci_square_to_mm("a", "10", board_mm, n, 0.0, 0.0)
    assert abs(y_top - 0.5 * sq) < 1e-6
    _, y_bottom = uci_square_to_mm("a", "1", board_mm, n, 0.0, 0.0)
    assert abs(y_bottom - (n - 0.5) * sq) < 1e-6


def test_move_to_gcode_simple_move_no_capture():
    lines = move_to_gcode("e2e4", capture=False)
    text = "\n".join(lines)
    assert "from e2" in text and "to e4" in text
    assert "to discard" not in text
    assert "M3" in text and "M5" in text


def test_plotter_uci_legs_castling_kingside():
    assert plotter_uci_legs("e1g1") == ["e1g1", "h1f1"]
    assert plotter_uci_legs("e8g8") == ["e8g8", "h8f8"]


def test_plotter_uci_legs_normal_single_leg():
    assert plotter_uci_legs("e2e4") == ["e2e4"]
    assert plotter_uci_legs("e7e8q") == ["e7e8"]


def test_move_to_gcode_en_passant_uses_victim_square():
    lines = move_to_gcode(
        "e5d6",
        capture=True,
        captured_piece_square="d5",
        board_size_mm=200.0,
        square_count=8,
    )
    text = "\n".join(lines)
    assert "en passant victim d5" in text
    assert "to d6" in text


def test_move_to_gcode_castling_includes_rook_leg():
    parts = [move_to_gcode(leg, False) for leg in plotter_uci_legs("e1g1")]
    flat = "\n".join("\n".join(p) for p in parts)
    assert "from e1" in flat and "to g1" in flat
    assert "from h1" in flat and "to f1" in flat


def test_move_to_gcode_capture_includes_discard():
    lines = move_to_gcode(
        "e2e4",
        capture=True,
        board_size_mm=200.0,
        square_count=8,
        origin_x=0.0,
        origin_y=0.0,
        discard_offset_squares=1.5,
    )
    text = "\n".join(lines)
    assert "to discard" in text
    square_size = 200.0 / 8
    discard_x = -1.5 * square_size
    assert f"X{discard_x:.2f}" in text


def test_api_health(flask_client):
    r = flask_client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "ok"


def test_chess_execute_move_ok_when_plotter_dry_run(flask_client):
    """README: use PLOTTER_DRY_RUN for no serial; execute-move must not require hardware."""
    r = flask_client.post(
        "/api/chess/execute-move",
        json={"uci": "e2e4", "capture": False},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("success") is True
    assert body.get("dry_run") is True


def test_chess_execute_move_castling_dry_run(flask_client):
    r = flask_client.post(
        "/api/chess/execute-move",
        json={"uci": "e1g1", "capture": False},
    )
    assert r.status_code == 200


def test_chess_execute_move_en_passant_dry_run(flask_client):
    r = flask_client.post(
        "/api/chess/execute-move",
        json={"uci": "e5d6", "capture": True, "captured_square": "d5"},
    )
    assert r.status_code == 200
