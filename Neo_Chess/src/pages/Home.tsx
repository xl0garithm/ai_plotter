import { useState } from "react";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import { CyberButton } from "@/components/CyberButton";
import { Trophy, Users, Bot, Cpu } from "lucide-react";
import type { GameMode, Difficulty } from "@/hooks/use-chess-engine";

type VoiceStyle = "harsh" | "sweet";

const MODES: { id: GameMode; label: string; desc: string; icon: React.ReactNode }[] = [
  {
    id: "pvp",
    label: "Player vs Player",
    desc: "Two human operatives",
    icon: <Users className="w-5 h-5" />,
  },
  {
    id: "pvai",
    label: "Player vs AI",
    desc: "Human vs CORTEX AI",
    icon: <Bot className="w-5 h-5" />,
  },
  {
    id: "aivai",
    label: "AI vs AI",
    desc: "Watch the machines clash",
    icon: <Cpu className="w-5 h-5" />,
  },
];

export default function Home() {
  const [_, setLocation] = useLocation();
  const [name, setName] = useState("");
  const [opponent, setOpponent] = useState("");
  const [gameMode, setGameMode] = useState<GameMode>("pvai");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [voiceStyle, setVoiceStyle] = useState<VoiceStyle>("harsh");

  const handleStart = () => {
    const p1 = name.trim() || "Cyber Mint";
    const p2 =
      gameMode === "pvp"
        ? opponent.trim() || "Cosmic Orchid"
        : gameMode === "aivai"
        ? "CORTEX-B"
        : "CORTEX AI";

    localStorage.setItem("playerName", p1);
    localStorage.setItem("opponentName", p2);
    localStorage.setItem("gameMode", gameMode);
    localStorage.setItem("difficulty", difficulty);
    localStorage.setItem("voiceStyle", voiceStyle);
    setLocation("/game");
  };

  const showOpponent = gameMode === "pvp";
  const showDifficulty = gameMode !== "pvp";

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/5 via-background to-background" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="glass-panel max-w-lg w-full p-8 md:p-12 relative z-10 border-t border-primary/50"
      >
        {/* Title */}
        <div className="text-center mb-10">
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ repeat: Infinity, duration: 2.5, repeatType: "reverse" }}
            className="inline-block mb-4 p-4 rounded-full bg-primary/10 border border-primary/40 shadow-[0_0_30px_rgba(0,243,255,0.3)]"
          >
            <span className="text-4xl select-none">♛</span>
          </motion.div>
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-black neon-text mb-2 tracking-tighter">
            NEO<span className="text-white">CHESS</span>
          </h1>
          <p className="text-muted-foreground font-mono uppercase tracking-widest text-xs">
            Cyberpunk Tactical Chess System
          </p>
        </div>

        <div className="space-y-7">
          {/* Game Mode */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-primary uppercase tracking-wider">
              Combat Protocol
            </label>
            <div className="grid grid-cols-3 gap-2">
              {MODES.map((mode) => (
                <button
                  key={mode.id}
                  data-testid={`mode-${mode.id}`}
                  onClick={() => setGameMode(mode.id)}
                  className={`
                    flex flex-col items-center gap-1.5 py-3 px-2 border transition-all text-center
                    ${
                      gameMode === mode.id
                        ? "border-primary bg-primary/10 text-primary shadow-[0_0_15px_rgba(0,243,255,0.3)]"
                        : "border-border text-muted-foreground hover:border-primary/40 hover:text-primary/70"
                    }
                  `}
                >
                  {mode.icon}
                  <span className="text-[9px] font-bold uppercase tracking-wider leading-tight">
                    {mode.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Player Names */}
          <div className="space-y-3">
            {gameMode === "aivai" ? (
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider" style={{ color: "#00f3ff" }}>
                  Operative ID (Cyber Mint)
                </div>
                <div className="text-xs text-muted-foreground">No input required — AI will use default codenames.</div>
              </div>
            ) : (
              <>
                <label className="text-xs font-bold uppercase tracking-wider" style={{ color: "#00f3ff" }}>
                  Operative ID (Cyber Mint)
                </label>
                <input
                  data-testid="input-player-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="ENTER CODENAME"
                  className="w-full bg-black/50 border border-border px-4 py-3 text-base font-mono text-white placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all uppercase"
                />
                {showOpponent && (
                  <div className="space-y-3">
                    <label className="text-xs font-bold uppercase tracking-wider" style={{ color: "#ff00ff" }}>
                      Operative ID (Cosmic Orchid)
                    </label>
                    <input
                      data-testid="input-opponent-name"
                      value={opponent}
                      onChange={(e) => setOpponent(e.target.value)}
                      placeholder="ENTER CODENAME"
                      className="w-full bg-black/50 border border-border px-4 py-3 text-base font-mono text-white placeholder:text-muted-foreground/40 focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-all uppercase"
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {/* Difficulty (AI modes only) */}
          {showDifficulty && (
            <div className="space-y-3">
              <label className="text-xs font-bold text-primary uppercase tracking-wider">
                AI Core Level
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["easy", "medium", "hard"] as Difficulty[]).map((level) => (
                  <button
                    key={level}
                    data-testid={`difficulty-${level}`}
                    onClick={() => setDifficulty(level)}
                    className={`
                      py-2.5 px-2 border transition-all uppercase text-xs font-bold tracking-widest
                      ${
                        difficulty === level
                          ? "border-secondary bg-secondary/10 text-secondary shadow-[0_0_15px_rgba(255,0,255,0.3)]"
                          : "border-border text-muted-foreground hover:border-secondary/40 hover:text-secondary/70"
                      }
                    `}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Voice Style */}
<div className="space-y-3">
  <label className="text-xs font-bold text-primary uppercase tracking-wider">
    AI Voice Profile
  </label>
  <div className="grid grid-cols-2 gap-2">
    {([
      { id: "harsh", label: "Gritty Rival", desc: "Cold. Brutal. Relentless.", icon: "💀" },
      { id: "sweet", label: "Soft Ally",   desc: "Warm. Playful. Charming.",  icon: "🌸" },
    ] as { id: VoiceStyle; label: string; desc: string; icon: string }[]).map((v) => (
      <button
        key={v.id}
        onClick={() => setVoiceStyle(v.id)}
        className={`
          flex flex-col items-center gap-1.5 py-3 px-2 border transition-all text-center
          ${voiceStyle === v.id
            ? "border-primary bg-primary/10 text-primary shadow-[0_0_15px_rgba(0,243,255,0.3)]"
            : "border-border text-muted-foreground hover:border-primary/40 hover:text-primary/70"}
        `}
      >
        <span className="text-xl">{v.icon}</span>
        <span className="text-[9px] font-bold uppercase tracking-wider leading-tight">{v.label}</span>
        <span className="text-[8px] text-muted-foreground">{v.desc}</span>
      </button>
    ))}
  </div>
</div>

          {/* Action Buttons */}
          <div className="pt-2 space-y-3">
            <CyberButton
              data-testid="button-start"
              onClick={handleStart}
              className="w-full h-13 text-lg"
            >
              INITIALIZE MATCH
            </CyberButton>

            <CyberButton
              variant="secondary"
              onClick={() => setLocation("/history")}
              className="w-full"
              data-testid="button-archives"
            >
              <span className="flex items-center justify-center gap-2">
                <Trophy className="w-4 h-4" /> ACCESS ARCHIVES
              </span>
            </CyberButton>
          </div>
        </div>
      </motion.div>

      {/* Decorative corners */}
      <div className="absolute top-8 left-8 w-28 h-28 border-l-2 border-t-2 border-primary/20 rounded-tl-3xl pointer-events-none" />
      <div className="absolute bottom-8 right-8 w-28 h-28 border-r-2 border-b-2 border-secondary/20 rounded-br-3xl pointer-events-none" />
    </div>
  );
}
