import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import { Board } from "@/components/Board";
import { CyberButton } from "@/components/CyberButton";
import { useChessEngine } from "@/hooks/use-chess-engine";
import { useCreateGame } from "@/hooks/use-games";
import { RefreshCw, LogOut } from "lucide-react";
import type { GameMode, Difficulty } from "@/hooks/use-chess-engine";

const PIECE_UNICODE: Record<string, string> = {
  p: "♟", r: "♜", n: "♞", b: "♝", q: "♛", k: "♚"
};

function CapturedPieces({ pieces, color }: { pieces: string[]; color: "w" | "b" }) {
  const glowClass = color === "w" ? "text-primary" : "text-secondary";
  return (
    <div className="flex flex-wrap gap-0.5 min-h-[20px]">
      {pieces.map((p, i) => (
        <span key={i} className={`text-base leading-none ${glowClass} opacity-80`}>
          {PIECE_UNICODE[p] || "♟"}
        </span>
      ))}
    </div>
  );
}

function PromotionModal({
  color,
  onSelect,
}: {
  color: "w" | "b";
  onSelect: (piece: "q" | "r" | "b" | "n") => void;
}) {
  const pieces: Array<{ type: "q" | "r" | "b" | "n"; label: string; symbol: string }> = [
    { type: "q", label: "Queen", symbol: color === "w" ? "♕" : "♛" },
    { type: "r", label: "Rook", symbol: color === "w" ? "♖" : "♜" },
    { type: "b", label: "Bishop", symbol: color === "w" ? "♗" : "♝" },
    { type: "n", label: "Knight", symbol: color === "w" ? "♘" : "♞" },
  ];

  const accentClass = color === "w" ? "border-primary text-primary" : "border-secondary text-secondary";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`glass-panel p-8 text-center border-t-2 ${color === "w" ? "border-t-primary" : "border-t-secondary"}`}
      >
        <h2 className={`text-2xl font-black mb-2 ${color === "w" ? "neon-text" : "text-secondary"}`}>
          PROMOTION
        </h2>
        <p className="text-muted-foreground font-mono text-sm mb-6 uppercase tracking-widest">
          Choose upgrade
        </p>
        <div className="grid grid-cols-4 gap-3">
          {pieces.map((p) => (
            <button
              key={p.type}
              data-testid={`promote-${p.type}`}
              onClick={() => onSelect(p.type)}
              className={`flex flex-col items-center gap-2 p-4 border ${accentClass} hover:bg-primary/10 transition-all`}
            >
              <span className="text-4xl">{p.symbol}</span>
              <span className="text-[9px] font-bold uppercase tracking-widest">{p.label}</span>
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

const EXECUTE_PLOTTER_KEY = "neo_chess_execute_plotter";

async function executeMoveOnPlotter(uci: string, capture: boolean): Promise<void> {
  const res = await fetch("/api/chess/execute-move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uci, capture }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Plotter error: ${res.status}`);
  }
}

export default function Game() {
  const [_, setLocation] = useLocation();

  const playerName = localStorage.getItem("playerName") || "OPERATIVE";
  const opponentName = localStorage.getItem("opponentName") || "CORTEX AI";
  const gameMode = (localStorage.getItem("gameMode") as GameMode) || "pvai";
  const difficulty = (localStorage.getItem("difficulty") as Difficulty) || "medium";

  const [executeOnPlotter, setExecuteOnPlotter] = useState(() =>
    localStorage.getItem(EXECUTE_PLOTTER_KEY) === "true"
  );
  const [plotterError, setPlotterError] = useState<string | null>(null);

  const executeRef = useRef(executeOnPlotter);
  executeRef.current = executeOnPlotter;

  const handlePlotterMove = useCallback(async (uci: string, capture: boolean) => {
    if (!executeRef.current) return;
    setPlotterError(null);
    try {
      await executeMoveOnPlotter(uci, capture);
    } catch (e) {
      setPlotterError(e instanceof Error ? e.message : "Plotter failed");
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(EXECUTE_PLOTTER_KEY, String(executeOnPlotter));
  }, [executeOnPlotter]);

  const { gameState, selectSquare, confirmPromotion, resetGame } = useChessEngine(gameMode, difficulty, handlePlotterMove);
  const { mutate: saveGame } = useCreateGame();
  const [hasSaved, setHasSaved] = useState(false);

  const whiteName = playerName;
  const blackName = gameMode === "pvp" ? opponentName : gameMode === "aivai" ? "CORTEX-A" : "CORTEX AI";
  const whiteLabel = gameMode === "aivai" ? "CORTEX-W" : playerName;

  // Victory confetti
  useEffect(() => {
    if (gameState.winner === "w" && gameMode !== "aivai") {
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ["#00f3ff", "#ffffff"] });
    }
  }, [gameState.winner, gameMode]);

  // Auto-save on game end
  useEffect(() => {
    if (gameState.isGameOver && !hasSaved) {
      let winnerLabel = "draw";
      if (gameState.winner === "w") winnerLabel = "white";
      else if (gameState.winner === "b") winnerLabel = "black";

      saveGame({
        playerName: whiteName,
        opponentName: blackName,
        gameMode,
        winner: winnerLabel,
        difficulty: gameMode === "pvp" ? "pvp" : difficulty,
        moves: gameState.moveCount,
      });
      setHasSaved(true);
    }
  }, [gameState.isGameOver, hasSaved, saveGame, whiteName, blackName, gameMode, difficulty, gameState.winner, gameState.moveCount]);

  const handleRestart = () => {
    resetGame();
    setHasSaved(false);
  };

  const isWhiteTurn = gameState.turn === "w";
  const isAiThinking =
    (gameMode === "pvai" && gameState.turn === "b" && !gameState.isGameOver) ||
    (gameMode === "aivai" && !gameState.isGameOver);

  const turnLabel = gameMode === "aivai"
    ? (isWhiteTurn ? "CORTEX-W Processing" : "CORTEX-B Processing")
    : gameMode === "pvp"
    ? (isWhiteTurn ? `${whiteName}'s Turn` : `${blackName}'s Turn`)
    : (isWhiteTurn ? "Your Turn" : "AI Processing...");

  function getWinnerMessage() {
    if (!gameState.isGameOver) return "";
    if (gameState.isDraw) return "DRAW";
    if (gameState.winner === "w") {
      if (gameMode === "pvai") return "MISSION COMPLETE";
      if (gameMode === "pvp") return `${whiteName} WINS`;
      return "CORTEX-W WINS";
    }
    if (gameMode === "pvai") return "SYSTEM FAILURE";
    if (gameMode === "pvp") return `${blackName} WINS`;
    return "CORTEX-B WINS";
  }

  function getWinnerSubtext() {
    if (gameState.isDraw) return "Stalemate or insufficient material";
    if (gameState.winner === "w") return gameMode === "pvai" ? "Enemy AI neutralized" : "Checkmate delivered";
    return gameMode === "pvai" ? "Tactical superiority lost" : "Checkmate delivered";
  }

  const winnerIsPlayer = gameState.winner === "w" && gameMode !== "aivai";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-3 relative overflow-hidden bg-background">
      {/* HUD Header */}
      <header className="fixed top-0 left-0 right-0 p-3 md:p-5 flex flex-col items-center z-30 pointer-events-none">
        <div className="absolute top-3 right-3 md:top-5 md:right-5 pointer-events-auto">
          <CyberButton
            onClick={() => setLocation("/")}
            variant="secondary"
            className="opacity-70 hover:opacity-100 transition-opacity"
            data-testid="button-abort"
          >
            <LogOut className="w-4 h-4 mr-1" /> ABORT
          </CyberButton>
        </div>

        <div className="text-center mb-3 pointer-events-none">
          <h1 className="text-lg md:text-2xl font-black neon-text tracking-widest font-orbitron opacity-70">
            NEO<span className="text-white">CHESS</span>
          </h1>
        </div>

        {/* Score bar */}
        <div className="flex items-center gap-8 pointer-events-auto bg-black/40 backdrop-blur-md px-6 py-3 border border-white/10 rounded-full shadow-[0_0_30px_rgba(0,243,255,0.08)]">
          {/* White side */}
          <div className="flex items-center gap-3">
            <div className={`h-9 w-9 border-2 border-primary bg-primary/10 rounded-full flex items-center justify-center text-primary text-xs font-bold shadow-[0_0_15px_rgba(0,243,255,0.3)] ${isWhiteTurn && !gameState.isGameOver ? "ring-2 ring-primary ring-offset-1 ring-offset-black" : ""}`}>
              ♔
            </div>
            <div>
              <div className="text-primary text-sm font-bold font-orbitron leading-none">{whiteLabel}</div>
              <CapturedPieces pieces={gameState.capturedByWhite} color="w" />
            </div>
          </div>

          <div className="text-muted-foreground font-mono text-xs px-3 text-center">
            <div className="text-white font-bold">{Math.ceil(gameState.moveCount / 2)}</div>
            <div className="text-[9px] uppercase tracking-widest">moves</div>
          </div>

          {/* Black side */}
          <div className="flex items-center gap-3 flex-row-reverse">
            <div className={`h-9 w-9 border-2 border-secondary bg-secondary/10 rounded-full flex items-center justify-center text-secondary text-xs font-bold shadow-[0_0_15px_rgba(255,0,255,0.3)] ${!isWhiteTurn && !gameState.isGameOver ? "ring-2 ring-secondary ring-offset-1 ring-offset-black" : ""}`}>
              ♚
            </div>
            <div className="text-right">
              <div className="text-secondary text-sm font-bold font-orbitron leading-none">{blackName}</div>
              <CapturedPieces pieces={gameState.capturedByBlack} color="b" />
            </div>
          </div>
        </div>
      </header>

      {/* Main board area */}
      <main className="w-full max-w-6xl z-10 pt-28 flex flex-col items-center gap-4">
        <Board gameState={gameState} onSquareClick={selectSquare} />

        {/* Turn indicator */}
        <div data-testid="turn-indicator" className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-3">
            <div className={`px-5 py-2 rounded-full border font-mono text-sm uppercase tracking-widest transition-all duration-300 ${
              isAiThinking
                ? "bg-secondary/20 border-secondary text-secondary shadow-[0_0_20px_rgba(255,0,255,0.4)] animate-pulse"
                : isWhiteTurn
                ? "bg-primary/20 border-primary text-primary shadow-[0_0_20px_rgba(0,243,255,0.4)]"
                : "bg-secondary/20 border-secondary text-secondary shadow-[0_0_20px_rgba(255,0,255,0.4)]"
            }`}>
              {turnLabel}
            </div>
            {gameState.isCheck && (
              <div className="px-4 py-2 rounded-full border border-destructive text-destructive font-mono text-sm uppercase tracking-widest animate-pulse">
                ⚡ CHECK
              </div>
            )}
          </div>
          <label className="flex items-center gap-2 cursor-pointer text-muted-foreground hover:text-foreground transition-colors">
            <input
              type="checkbox"
              checked={executeOnPlotter}
              onChange={(e) => setExecuteOnPlotter(e.target.checked)}
              className="rounded border-border"
            />
            <span className="font-mono text-xs uppercase tracking-widest">Execute on plotter</span>
          </label>
          {plotterError && (
            <div className="px-4 py-2 rounded border border-destructive text-destructive font-mono text-xs">
              {plotterError}
            </div>
          )}
        </div>
      </main>

      {/* Ambient glow */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        <div className="absolute top-[10%] left-[5%] w-64 h-64 bg-primary/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-[10%] right-[5%] w-64 h-64 bg-secondary/10 rounded-full blur-[100px]" />
      </div>

      {/* Promotion Modal */}
      {gameState.promotionPending && (
        <PromotionModal
          color={gameState.turn}
          onSelect={confirmPromotion}
        />
      )}

      {/* Game Over Modal */}
      <AnimatePresence>
        {gameState.isGameOver && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
            <motion.div
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.85, opacity: 0 }}
              className={`glass-panel max-w-md w-full p-8 text-center border-t-2 ${winnerIsPlayer ? "border-t-primary" : gameState.isDraw ? "border-t-yellow-500" : "border-t-destructive"}`}
            >
              <h2 className={`text-4xl md:text-5xl font-black mb-2 ${
                gameState.isDraw
                  ? "text-yellow-400 drop-shadow-[0_0_15px_rgba(255,204,0,0.8)]"
                  : winnerIsPlayer
                  ? "text-primary drop-shadow-[0_0_15px_rgba(0,243,255,0.8)]"
                  : "text-destructive drop-shadow-[0_0_15px_rgba(255,0,0,0.8)]"
              }`}
              data-testid="game-over-title"
              >
                {getWinnerMessage()}
              </h2>

              <p className="text-muted-foreground font-mono mb-8 uppercase tracking-widest text-sm">
                {getWinnerSubtext()} · {Math.ceil(gameState.moveCount / 2)} moves
              </p>

              <div className="flex flex-col gap-3">
                <CyberButton onClick={handleRestart} className="w-full" data-testid="button-restart">
                  <span className="flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4" /> REBOOT MATCH
                  </span>
                </CyberButton>
                <CyberButton onClick={() => setLocation("/")} variant="secondary" className="w-full" data-testid="button-exit">
                  <span className="flex items-center justify-center gap-2">
                    <LogOut className="w-4 h-4" /> ABORT MISSION
                  </span>
                </CyberButton>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
