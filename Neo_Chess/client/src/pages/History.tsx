import { useGames } from "@/hooks/use-games";
import { CyberButton } from "@/components/CyberButton";
import { Link } from "wouter";
import { ArrowLeft, Trophy, AlertTriangle, Minus, Users, Bot, Cpu } from "lucide-react";
import { format } from "date-fns";
import { motion } from "framer-motion";

const MODE_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  pvp: { label: "PvP", icon: <Users className="w-3.5 h-3.5" /> },
  pvai: { label: "vs AI", icon: <Bot className="w-3.5 h-3.5" /> },
  aivai: { label: "AI vs AI", icon: <Cpu className="w-3.5 h-3.5" /> },
};

export default function History() {
  const { data: games } = useGames();

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-5xl mx-auto">
      <header className="flex justify-between items-center mb-12">
        <Link href="/" className="group flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors">
          <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          <span className="font-mono uppercase tracking-widest text-sm">Back to Hub</span>
        </Link>
        <h1 className="text-2xl md:text-3xl font-bold neon-text tracking-wide">GAME ARCHIVES</h1>
      </header>

      {!games || games.length === 0 ? (
        <div className="text-center text-muted-foreground p-12 glass-panel">
          <div className="text-5xl mb-4 opacity-30">♛</div>
          <p className="font-mono uppercase tracking-widest mb-4">NO MATCHES ON RECORD</p>
          <Link href="/game" className="text-primary hover:underline font-mono uppercase text-sm">
            INITIATE FIRST MATCH →
          </Link>
        </div>
      ) : (
        <div className="grid gap-3">
          {games.map((game, i) => {
            const isWhiteWin = game.winner === "white";
            const isBlackWin = game.winner === "black";
            const isDraw = game.winner === "draw";
            const modeInfo = MODE_LABELS[game.gameMode || "pvai"];

            return (
              <motion.div
                key={game.id}
                data-testid={`game-record-${game.id}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="glass-panel p-5 flex flex-col md:flex-row items-start md:items-center justify-between group hover:border-primary/50 transition-colors gap-4"
              >
                <div className="flex items-center gap-5">
                  {/* Result icon */}
                  <div className={`
                    w-11 h-11 rounded-full flex items-center justify-center border-2 flex-shrink-0
                    ${isDraw
                      ? "border-yellow-500 text-yellow-400 bg-yellow-500/10"
                      : isWhiteWin
                      ? "border-primary text-primary bg-primary/10 shadow-[0_0_12px_rgba(0,243,255,0.3)]"
                      : "border-destructive text-destructive bg-destructive/10 shadow-[0_0_12px_rgba(255,0,0,0.3)]"}
                  `}>
                    {isDraw
                      ? <Minus className="w-5 h-5" />
                      : isWhiteWin
                      ? <Trophy className="w-5 h-5" />
                      : <AlertTriangle className="w-5 h-5" />}
                  </div>

                  {/* Match info */}
                  <div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-lg font-bold text-white">
                        {game.playerName}
                      </span>
                      <span className="text-muted-foreground font-mono text-sm">vs</span>
                      <span className="text-lg font-bold text-secondary">
                        {game.opponentName || "CORTEX AI"}
                      </span>
                      {modeInfo && (
                        <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border border-muted-foreground/20 text-muted-foreground uppercase font-mono">
                          {modeInfo.icon} {modeInfo.label}
                        </span>
                      )}
                      {game.difficulty && game.difficulty !== "pvp" && (
                        <span className="text-[10px] px-2 py-0.5 rounded border border-secondary/20 text-secondary/70 uppercase font-mono">
                          {game.difficulty}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono mt-1">
                      {format(new Date(game.createdAt || new Date()), "yyyy-MM-dd HH:mm")}
                      {" · "}
                      {game.moves} half-moves ({Math.ceil(game.moves / 2)} full)
                    </div>
                  </div>
                </div>

                {/* Result label */}
                <div className={`
                  text-xl font-black uppercase tracking-widest flex-shrink-0
                  ${isDraw ? "text-yellow-400" : isWhiteWin ? "neon-text" : "text-muted-foreground opacity-50"}
                `}>
                  {isDraw ? "DRAW" : isWhiteWin ? "WHITE WINS" : "BLACK WINS"}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      <div className="mt-8 text-center">
        <CyberButton onClick={() => { localStorage.removeItem("neo_chess_history"); window.location.reload(); }} variant="secondary" className="text-xs opacity-60 hover:opacity-100">
          CLEAR ARCHIVES
        </CyberButton>
      </div>
    </div>
  );
}
