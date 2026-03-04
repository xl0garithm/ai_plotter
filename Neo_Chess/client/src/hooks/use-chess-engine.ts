import { useState, useEffect, useCallback, useRef } from "react";
import { Chess } from "chess.js";

export type GameMode = "pvp" | "pvai" | "aivai";
export type Difficulty = "easy" | "medium" | "hard";

export interface ChessGameState {
  fen: string;
  turn: "w" | "b";
  selectedSquare: string | null;
  validMoveSquares: string[];
  isCheck: boolean;
  isCheckmate: boolean;
  isDraw: boolean;
  isGameOver: boolean;
  winner: "w" | "b" | "draw" | null;
  capturedByWhite: string[];
  capturedByBlack: string[];
  moveCount: number;
  lastMove: { from: string; to: string } | null;
  gameMode: GameMode;
  promotionPending: { from: string; to: string } | null;
}

// Piece square tables for AI evaluation
const PIECE_SQUARE_TABLES: Record<string, number[][]> = {
  p: [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5,  5, 10, 25, 25, 10,  5,  5],
    [0,  0,  0, 20, 20,  0,  0,  0],
    [5, -5,-10,  0,  0,-10, -5,  5],
    [5, 10, 10,-20,-20, 10, 10,  5],
    [0,  0,  0,  0,  0,  0,  0,  0]
  ],
  n: [
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50]
  ],
  b: [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
  ],
  r: [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [5, 10, 10, 10, 10, 10, 10,  5],
    [-5,  0,  0,  0,  0,  0,  0, -5],
    [-5,  0,  0,  0,  0,  0,  0, -5],
    [-5,  0,  0,  0,  0,  0,  0, -5],
    [-5,  0,  0,  0,  0,  0,  0, -5],
    [-5,  0,  0,  0,  0,  0,  0, -5],
    [0,  0,  0,  5,  5,  0,  0,  0]
  ],
  q: [
    [-20,-10,-10, -5, -5,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5,  5,  5,  5,  0,-10],
    [-5,  0,  5,  5,  5,  5,  0, -5],
    [0,  0,  5,  5,  5,  5,  0, -5],
    [-10,  5,  5,  5,  5,  5,  0,-10],
    [-10,  0,  5,  0,  0,  0,  0,-10],
    [-20,-10,-10, -5, -5,-10,-10,-20]
  ],
  k: [
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [20, 20,  0,  0,  0,  0, 20, 20],
    [20, 30, 10,  0,  0, 10, 30, 20]
  ]
};

const PIECE_VALUES: Record<string, number> = {
  p: 100, n: 320, b: 330, r: 500, q: 900, k: 20000
};

function squareToIndex(square: string): [number, number] {
  const file = square.charCodeAt(0) - 97;
  const rank = 8 - parseInt(square[1]);
  return [rank, file];
}

function evaluatePosition(chess: Chess): number {
  if (chess.isCheckmate()) {
    return chess.turn() === "w" ? -100000 : 100000;
  }
  if (chess.isDraw()) return 0;

  let score = 0;
  const board = chess.board();

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const piece = board[r][c];
      if (!piece) continue;

      const pst = PIECE_SQUARE_TABLES[piece.type];
      const tableRow = piece.color === "w" ? 7 - r : r;
      const tableScore = pst ? pst[tableRow][c] : 0;
      const pieceValue = PIECE_VALUES[piece.type] + tableScore;

      score += piece.color === "w" ? pieceValue : -pieceValue;
    }
  }

  return score;
}

function minimax(
  chess: Chess,
  depth: number,
  alpha: number,
  beta: number,
  maximizing: boolean
): number {
  if (depth === 0 || chess.isGameOver()) {
    return evaluatePosition(chess);
  }

  const moves = chess.moves({ verbose: false });

  if (maximizing) {
    let maxEval = -Infinity;
    for (const move of moves) {
      chess.move(move);
      const evalScore = minimax(chess, depth - 1, alpha, beta, false);
      chess.undo();
      if (evalScore > maxEval) maxEval = evalScore;
      alpha = Math.max(alpha, evalScore);
      if (beta <= alpha) break;
    }
    return maxEval;
  } else {
    let minEval = Infinity;
    for (const move of moves) {
      chess.move(move);
      const evalScore = minimax(chess, depth - 1, alpha, beta, true);
      chess.undo();
      if (evalScore < minEval) minEval = evalScore;
      beta = Math.min(beta, evalScore);
      if (beta <= alpha) break;
    }
    return minEval;
  }
}

function getBestMove(chess: Chess, difficulty: Difficulty): string | null {
  const moves = chess.moves({ verbose: false });
  if (moves.length === 0) return null;

  if (difficulty === "easy") {
    // Random move with slight preference for captures
    const captures = moves.filter(m => m.includes("x"));
    const pool = captures.length > 0 && Math.random() > 0.5 ? captures : moves;
    return pool[Math.floor(Math.random() * pool.length)];
  }

  const depth = difficulty === "medium" ? 2 : 3;
  const maximizing = chess.turn() === "w";

  let bestMove = moves[0];
  let bestScore = maximizing ? -Infinity : Infinity;

  for (const move of moves) {
    chess.move(move);
    const score = minimax(chess, depth - 1, -Infinity, Infinity, !maximizing);
    chess.undo();

    if ((maximizing && score > bestScore) || (!maximizing && score < bestScore)) {
      bestScore = score;
      bestMove = move;
    }
  }

  return bestMove;
}

function computeCaptured(chess: Chess): { byWhite: string[], byBlack: string[] } {
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

  const byWhite: string[] = [];
  const byBlack: string[] = [];

  for (const [type, start] of Object.entries(startCount)) {
    const missingBlack = start - (blackCount[type] || 0);
    const missingWhite = start - (whiteCount[type] || 0);
    for (let i = 0; i < missingBlack; i++) byWhite.push(type);
    for (let i = 0; i < missingWhite; i++) byBlack.push(type);
  }

  return { byWhite, byBlack };
}

function buildGameState(
  chess: Chess,
  selectedSquare: string | null,
  gameMode: GameMode,
  promotionPending: { from: string; to: string } | null,
  lastMove: { from: string; to: string } | null
): ChessGameState {
  let winner: "w" | "b" | "draw" | null = null;
  if (chess.isCheckmate()) winner = chess.turn() === "w" ? "b" : "w";
  else if (chess.isDraw()) winner = "draw";

  let validMoveSquares: string[] = [];
  if (selectedSquare) {
    const moves = chess.moves({ square: selectedSquare as any, verbose: true });
    validMoveSquares = moves.map(m => m.to);
  }

  const { byWhite, byBlack } = computeCaptured(chess);

  return {
    fen: chess.fen(),
    turn: chess.turn() as "w" | "b",
    selectedSquare,
    validMoveSquares,
    isCheck: chess.isCheck(),
    isCheckmate: chess.isCheckmate(),
    isDraw: chess.isDraw(),
    isGameOver: chess.isGameOver(),
    winner,
    capturedByWhite: byWhite,
    capturedByBlack: byBlack,
    moveCount: chess.history().length,
    lastMove,
    gameMode,
    promotionPending,
  };
}

export function useChessEngine(gameMode: GameMode, difficulty: Difficulty) {
  const chessRef = useRef(new Chess());
  const [gameState, setGameState] = useState<ChessGameState>(() =>
    buildGameState(chessRef.current, null, gameMode, null, null)
  );
  const aiThinkingRef = useRef(false);

  const isHumanTurn = useCallback((turn: "w" | "b") => {
    if (gameMode === "pvp") return true;
    if (gameMode === "pvai") return turn === "w";
    return false; // aivai
  }, [gameMode]);

  const updateState = useCallback((sq: string | null = null, promo: { from: string; to: string } | null = null, lastMove: { from: string; to: string } | null = null) => {
    setGameState(buildGameState(chessRef.current, sq, gameMode, promo, lastMove));
  }, [gameMode]);

  const selectSquare = useCallback((square: string) => {
    const chess = chessRef.current;
    if (chess.isGameOver()) return;

    const currentTurn = chess.turn() as "w" | "b";
    if (!isHumanTurn(currentTurn)) return;

    const currentSelected = gameState.selectedSquare;

    // If a square is already selected, try to move
    if (currentSelected) {
      const validTargets = chess.moves({ square: currentSelected as any, verbose: true }).map(m => m.to);

      if (validTargets.includes(square)) {
        // Check for pawn promotion
        const piece = chess.get(currentSelected as any);
        const targetRank = square[1];
        if (piece?.type === "p" && ((piece.color === "w" && targetRank === "8") || (piece.color === "b" && targetRank === "1"))) {
          updateState(null, { from: currentSelected, to: square }, null);
          return;
        }

        try {
          const moveResult = chess.move({ from: currentSelected as any, to: square as any });
          if (moveResult) {
            updateState(null, null, { from: currentSelected, to: square });
          }
        } catch {
          updateState(null, null, null);
        }
        return;
      }
    }

    // Select new square
    const piece = chess.get(square as any);
    if (piece && piece.color === currentTurn) {
      updateState(square, null, gameState.lastMove);
    } else {
      updateState(null, null, gameState.lastMove);
    }
  }, [gameState.selectedSquare, gameState.lastMove, isHumanTurn, updateState]);

  const confirmPromotion = useCallback((promoteTo: "q" | "r" | "b" | "n") => {
    const pending = gameState.promotionPending;
    if (!pending) return;
    const chess = chessRef.current;

    try {
      const moveResult = chess.move({ from: pending.from as any, to: pending.to as any, promotion: promoteTo });
      if (moveResult) {
        updateState(null, null, { from: pending.from, to: pending.to });
      }
    } catch {
      updateState(null, null, gameState.lastMove);
    }
  }, [gameState.promotionPending, gameState.lastMove, updateState]);

  const resetGame = useCallback(() => {
    chessRef.current = new Chess();
    aiThinkingRef.current = false;
    setGameState(buildGameState(chessRef.current, null, gameMode, null, null));
  }, [gameMode]);

  // AI move effect
  useEffect(() => {
    const chess = chessRef.current;
    const state = gameState;

    if (state.isGameOver || state.promotionPending) return;
    if (isHumanTurn(state.turn)) return;
    if (aiThinkingRef.current) return;

    aiThinkingRef.current = true;
    const delay = gameMode === "aivai" ? 600 : 800;

    const timer = setTimeout(() => {
      const bestMove = getBestMove(chess, difficulty);
      if (bestMove) {
        try {
          const result = chess.move(bestMove);
          if (result) {
            aiThinkingRef.current = false;
            updateState(null, null, { from: result.from, to: result.to });
          }
        } catch {
          aiThinkingRef.current = false;
        }
      } else {
        aiThinkingRef.current = false;
        updateState(null, null, null);
      }
    }, delay);

    return () => {
      clearTimeout(timer);
      aiThinkingRef.current = false;
    };
  }, [gameState.turn, gameState.isGameOver, gameState.promotionPending, gameMode, difficulty, isHumanTurn, updateState]);

  return {
    gameState,
    selectSquare,
    confirmPromotion,
    resetGame,
  };
}
