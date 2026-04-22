import type { Chess, Color, Move, PieceSymbol, Square } from "chess.js";

/** POST JSON body matches Flask `/api/chess/move` (see `ChessMoveData`). */
export interface PhysicalChessMovePayload {
  from: Square;
  to: Square;
  piece: PieceSymbol;
  color: Color;
  flags: string | number;
  captured: PieceSymbol | null;
  promotion: PieceSymbol | null;
  capture_index: number;
}

export function physicalChessEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_PHYSICAL_CHESS !== "false";
}

export function chessApiBase(): string {
  return (import.meta.env.VITE_CHESS_API_BASE ?? "").replace(/\/$/, "");
}

/** Full URL for Flask ``POST /api/chess/move`` (respects ``VITE_CHESS_API_BASE``). */
export function chessMovePostUrl(): string {
  return `${chessApiBase()}/api/chess/move`;
}

/** Count pieces missing from each side (tray lengths) before a move. */
export function captureTrayLengthsBeforeMove(chess: Chess): { byWhite: number; byBlack: number } {
  const startCount: Record<string, number> = { p: 8, n: 2, b: 2, r: 2, q: 1 };
  const whiteCount: Record<string, number> = { p: 0, n: 0, b: 0, r: 0, q: 0 };
  const blackCount: Record<string, number> = { p: 0, n: 0, b: 0, r: 0, q: 0 };

  const board = chess.board();
  for (const row of board) {
    for (const piece of row) {
      if (!piece || piece.type === "k") continue;
      if (piece.color === "w") whiteCount[piece.type] = (whiteCount[piece.type] || 0) + 1;
      else blackCount[piece.type] = (blackCount[piece.type] || 0) + 1;
    }
  }

  let byWhite = 0;
  let byBlack = 0;
  for (const type of Object.keys(startCount)) {
    const start = startCount[type]!;
    byWhite += Math.max(0, start - (blackCount[type] || 0));
    byBlack += Math.max(0, start - (whiteCount[type] || 0));
  }
  return { byWhite, byBlack };
}

export function buildPhysicalMovePayload(
  move: Move,
  preCapturedByWhite: number,
  preCapturedByBlack: number,
): PhysicalChessMovePayload {
  const captured = move.captured;
  const capture_index =
    captured !== undefined
      ? move.color === "w"
        ? preCapturedByWhite
        : preCapturedByBlack
      : 0;

  return {
    from: move.from,
    to: move.to,
    piece: move.piece,
    color: move.color,
    flags: move.flags,
    captured: captured ?? null,
    promotion: move.promotion ?? null,
    capture_index,
  };
}

/**
 * Fire-and-forget notify to the plotter backend. Errors are logged only.
 * Same-origin: leave `VITE_CHESS_API_BASE` empty (default).
 * Cross-origin dev: e.g. `VITE_CHESS_API_BASE=http://127.0.0.1:5000`.
 */
export function notifyPhysicalChessMove(payload: PhysicalChessMovePayload): void {
  if (!physicalChessEnabled()) return;

  void fetch(chessMovePostUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch((err: unknown) => {
    console.warn("[physical chess] POST /api/chess/move failed:", err);
  });
}
