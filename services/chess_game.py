"""Chess play session: human v human, human v computer, computer v computer."""

from __future__ import annotations

import os
from typing import Optional

import chess
import chess.engine

PLAY_MODES = ("human_v_human", "human_v_computer", "computer_v_computer")

# Stockfish "Skill Level" UCI option (0–20). Not from chess.js (logic only; no AI).
DIFFICULTY_LEVELS = {"easy": 2, "medium": 8, "hard": 14, "strongest": 20}
DEFAULT_DIFFICULTY = "medium"


def _engine_path() -> str:
    return os.environ.get("STOCKFISH_PATH", "stockfish")


class ChessPlaySession:
    """Single game session. Mode and board state."""

    def __init__(self, mode: str = "human_v_human") -> None:
        self.mode = mode if mode in PLAY_MODES else "human_v_human"
        self.board = chess.Board()
        self._engine: Optional[chess.engine.SimpleEngine] = None
        self._movetime_s = 0.5
        self._difficulty = DEFAULT_DIFFICULTY
        self._skill_level = DIFFICULTY_LEVELS.get(DEFAULT_DIFFICULTY, 10)

    def _ensure_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(_engine_path())
            self._engine.configure({"Skill Level": self._skill_level})
        return self._engine

    def set_difficulty(self, level: str) -> None:
        key = (level or "").strip().lower() or DEFAULT_DIFFICULTY
        if key in DIFFICULTY_LEVELS:
            self._difficulty = key
            self._skill_level = DIFFICULTY_LEVELS[key]
            if self._engine is not None:
                try:
                    self._engine.configure({"Skill Level": self._skill_level})
                except Exception:
                    pass

    def get_difficulty(self) -> str:
        return self._difficulty

    def play_move(self, uci: str) -> bool:
        move = chess.Move.from_uci(uci)
        if move in self.board.legal_moves:
            self.board.push(move)
            return True
        return False

    def get_ai_move(self) -> Optional[str]:
        if self.board.is_game_over():
            return None
        try:
            engine = self._ensure_engine()
            result = engine.play(self.board, chess.engine.Limit(time=self._movetime_s))
            if result.move is None:
                return None
            self.board.push(result.move)
            return result.move.uci()
        except (FileNotFoundError, chess.engine.EngineTerminatedError):
            return None

    def is_capture(self, uci: str) -> bool:
        move = chess.Move.from_uci(uci)
        return self.board.is_capture(move)

    def get_fen(self) -> str:
        return self.board.fen()

    def is_white_turn(self) -> bool:
        return self.board.turn == chess.WHITE

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def result(self) -> str:
        return self.board.result()

    def set_mode(self, mode: str) -> None:
        if mode in PLAY_MODES:
            self.mode = mode

    def reset(self) -> None:
        self.board.reset()

    def quit_engine(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None


# One session per process (single user)
_session: Optional[ChessPlaySession] = None


def get_session() -> ChessPlaySession:
    global _session
    if _session is None:
        _session = ChessPlaySession()
    return _session
