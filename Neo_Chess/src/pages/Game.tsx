import { useEffect, useState, useRef } from "react";
import { useLocation } from "wouter";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";

import { Board } from "@/components/Board";
import { CyberButton } from "@/components/CyberButton";

import { useChessEngine } from "@/hooks/use-chess-engine";
import { useCreateGame } from "@/hooks/use-games";
import { useAudioManager } from "@/hooks/use-audio-manager";

import { AudioEvent } from "../../public/audio/events";

import { RefreshCw, LogOut, Volume2, VolumeX } from "lucide-react";

import type { GameMode, Difficulty } from "@/hooks/use-chess-engine";
import type { GameWinner } from "@/types/game";

const PIECE_UNICODE: Record<string, string> = {
  p: "♟",
  r: "♜",
  n: "♞",
  b: "♝",
  q: "♛",
  k: "♚",
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
  const pieces = [
    { type: "q", label: "Queen", symbol: color === "w" ? "♕" : "♛" },
    { type: "r", label: "Rook", symbol: color === "w" ? "♖" : "♜" },
    { type: "b", label: "Bishop", symbol: color === "w" ? "♗" : "♝" },
    { type: "n", label: "Knight", symbol: color === "w" ? "♘" : "♞" },
  ] as const;

  const accentClass = color === "w" ? "border-primary text-primary" : "border-secondary text-secondary";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`glass-panel p-8 text-center border-t-2 ${
          color === "w" ? "border-t-primary" : "border-t-secondary"
        }`}
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

export default function Game() {
  const [_, setLocation] = useLocation();

  const playerName = localStorage.getItem("playerName") || "OPERATIVE";
  const opponentName = localStorage.getItem("opponentName") || "CORTEX AI";
  const gameMode = (localStorage.getItem("gameMode") as GameMode) || "pvai";
  const difficulty = (localStorage.getItem("difficulty") as Difficulty) || "medium";
  const voiceStyle = (localStorage.getItem("voiceStyle") as "harsh" | "sweet") || "harsh";

  const whiteName = playerName;
  const blackName = gameMode === "pvp" ? opponentName : gameMode === "aivai" ? "CORTEX-A" : "Storm AI";

  const { gameState, selectSquare, confirmPromotion, resetGame } =
    useChessEngine(gameMode, difficulty, whiteName, blackName);

  const { mutate: saveGame } = useCreateGame();
  const { playAudio, toggleMute, isMuted } = useAudioManager(voiceStyle);

  const [hasSaved, setHasSaved] = useState(false);

  const prevGameStateRef = useRef(gameState);

  const isWhiteTurn = gameState.turn === "w";

  /* ----------------------------- GAME START AUDIO ---------------------------- */

  useEffect(() => {
    if (gameMode === "aivai") return;
    playAudio(AudioEvent.GAME_START);
  }, [gameMode, playAudio]);

  useEffect(() => {
    fetch("/api/chess/home", { method: "POST" }).catch((error) => {
      console.error("Failed to home robot at game start:", error);
    });
  }, []);

  /* ----------------------------- AI MOVE AUDIO ---------------------------- */

  useEffect(() => {
    if (gameMode === "aivai") return;

    const prev = prevGameStateRef.current;

    if (
      prev &&
      prev.moveCount !== gameState.moveCount &&
      gameMode !== "pvp" &&
      gameState.turn === "w"
    ) {
      let audioEvent;

      if (gameState.capturedByWhite.length > prev.capturedByWhite.length) {
        audioEvent = AudioEvent.PLAYER_KING;
      } else if (gameState.isCheck && !prev.isCheck) {
        audioEvent = AudioEvent.AI_KING;
      } else if (gameState.capturedByBlack.length > prev.capturedByBlack.length) {
        audioEvent =
          Math.random() < 0.5
            ? AudioEvent.AI_STRONG_MOVE
            : AudioEvent.AI_MOVE;
      } else if (Math.random() < 0.15) {
        audioEvent = AudioEvent.AI_TAUNT;
      } else {
        audioEvent = AudioEvent.PLAYER_TURN;
      }

      setTimeout(() => {
        playAudio(audioEvent);
      }, 350);
    }
  }, [
    gameState.moveCount,
    gameState.turn,
    gameState.isCheck,
    gameState.capturedByWhite.length,
    gameState.capturedByBlack.length,
  ]);

  useEffect(() => {
    prevGameStateRef.current = gameState;
  }, [gameState]);

  /* ----------------------------- CONFETTI ---------------------------- */

  useEffect(() => {
    if (gameState.winner === "w" && gameMode !== "aivai") {
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#00f3ff", "#ffffff"],
      });
    }
  }, [gameState.winner]);

  /* ----------------------------- SAVE GAME ---------------------------- */

  useEffect(() => {
    if (gameState.isGameOver && !hasSaved) {
      let winnerLabel: GameWinner = "draw";

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
  }, [gameState.isGameOver]);

  /* ----------------------------- GAME OVER AUDIO ---------------------------- */

  useEffect(() => {
    if (gameMode === "aivai") return;

    if (gameState.isGameOver && gameState.winner) {
      if (gameState.winner === "w") {
        playAudio(AudioEvent.PLAYER_VICTORY);
      } else if (gameMode !== "pvp") {
        playAudio(AudioEvent.AI_VICTORY);
      }
    }
  }, [gameState.isGameOver, gameState.winner, gameMode, playAudio]);

  const handleRestart = () => {
    resetGame();
    setHasSaved(false);
  };

  const turnLabel =
    gameMode === "pvp"
      ? isWhiteTurn
        ? `${whiteName}'s Turn`
        : `${blackName}'s Turn`
      : isWhiteTurn
      ? "Your Turn"
      : "AI Processing...";

  const winnerIsPlayer = gameState.winner === "w" && gameMode !== "aivai";
  const isGameActive = !gameState.isGameOver;
  const whiteIsActive = isGameActive && gameState.turn === "w";
  const blackIsActive = isGameActive && gameState.turn === "b";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-3 relative overflow-hidden bg-background">

      {/* TITLE */}
      <h1 className="mb-2 select-none text-[2.5rem] leading-none font-black tracking-[0.22em] md:text-5xl">
        <span className="text-primary drop-shadow-[0_0_6px_rgba(0,243,255,0.95)] [text-shadow:0_0_10px_rgba(0,243,255,0.95),0_0_26px_rgba(0,243,255,0.6)]">
          NEO
        </span>
        <span className="ml-2 bg-gradient-to-b from-zinc-100 via-slate-300 to-zinc-500 bg-clip-text text-transparent drop-shadow-[0_2px_0_rgba(255,255,255,0.35)] [text-shadow:0_1px_0_rgba(255,255,255,0.5),0_8px_18px_rgba(0,0,0,0.75)]">
          CHESS
        </span>
      </h1>

      {/* PLAYER NAMES */}
      <div className="w-full max-w-xl mb-2 rounded-2xl border border-white/10 bg-black/70 px-4 py-3 shadow-[0_0_30px_rgba(0,0,0,0.55)] backdrop-blur-sm">
        <div className="flex items-center justify-between gap-3 text-sm font-mono">
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full transition-all ${
                whiteIsActive ? "bg-primary animate-pulse shadow-[0_0_14px_rgba(0,243,255,0.95)]" : "bg-primary/30"
              }`}
            />
            <span className="font-black text-primary drop-shadow-[0_0_8px_rgba(0,243,255,0.9)]">
              {whiteName}
            </span>
            {whiteIsActive && (
              <span className="rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[10px] font-bold tracking-widest text-primary">
                TURN
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {blackIsActive && (
              <span className="rounded-full border border-secondary/40 bg-secondary/10 px-2 py-0.5 text-[10px] font-bold tracking-widest text-secondary">
                TURN
              </span>
            )}
            <span className="font-black text-secondary drop-shadow-[0_0_8px_rgba(255,58,141,0.9)]">
              {blackName}
            </span>
            <span
              className={`h-2.5 w-2.5 rounded-full transition-all ${
                blackIsActive ? "bg-secondary animate-pulse shadow-[0_0_14px_rgba(255,58,141,0.95)]" : "bg-secondary/30"
              }`}
            />
          </div>
        </div>
      </div>

      {/* CAPTURED PIECES */}
      <div className="flex justify-between w-full max-w-xl mb-3">
        <CapturedPieces pieces={gameState.capturedByWhite} color="w" />
        <CapturedPieces pieces={gameState.capturedByBlack} color="b" />
      </div>

      {/* CONTROLS */}
      <div className="absolute top-4 right-4 flex gap-2">
        <CyberButton onClick={toggleMute} variant="secondary">
          {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </CyberButton>

        <CyberButton onClick={() => setLocation("/")} variant="secondary">
          <LogOut size={16} />
        </CyberButton>
      </div>

      {/* BOARD */}
      <Board gameState={gameState} onSquareClick={selectSquare} />

      {/* TURN LABEL */}
      <div className="mt-4 text-sm font-mono tracking-widest text-muted-foreground">
        {turnLabel}
      </div>

      {gameState.promotionPending && (
        <PromotionModal color={gameState.turn} onSelect={confirmPromotion} />
      )}

      {/* GAME OVER MODAL */}
      <AnimatePresence>
        {gameState.isGameOver && (
          <div className="fixed inset-0 flex items-center justify-center bg-black/85 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.85, opacity: 0 }}
              className="glass-panel max-w-md w-full p-8 text-center"
            >
              <h2 className="text-4xl font-black mb-4">
                {winnerIsPlayer ? "MISSION COMPLETE" : "SYSTEM FAILURE"}
              </h2>

              <div className="flex flex-col gap-3">
                <CyberButton onClick={handleRestart}>
                  <RefreshCw className="w-4 h-4" /> REBOOT MATCH
                </CyberButton>

                <CyberButton onClick={() => setLocation("/")} variant="secondary">
                  <LogOut className="w-4 h-4" /> EXIT
                </CyberButton>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
