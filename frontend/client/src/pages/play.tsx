import { useState, useEffect, useCallback, Suspense } from "react";
import { useLocation } from "wouter";
import { Chess } from "chess.js";
import { Layout } from "@/components/layout";
import { CyberButton } from "@/components/cyber-button";
import { useSaveGame } from "@/hooks/use-games";
import { makeAIMove } from "@/lib/ai";
import { useToast } from "@/hooks/use-toast";
import { Cpu, User, ArrowLeft, Save } from "lucide-react";
import { Canvas } from "@react-three/fiber";
import { Board3D } from "@/components/board-3d";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";

export default function Play() {
  const [location, setLocation] = useLocation();
  const { toast } = useToast();
  
  // Parse match setup from URL
  const searchParams = new URLSearchParams(window.location.search);
  const mode = searchParams.get("mode") || "pva";
  const p1 = searchParams.get("p1") || "Player 1";
  const p2 = searchParams.get("p2") || "AI";

  const [game, setGame] = useState(new Chess());
  const [gameOver, setGameOver] = useState(false);
  const [resultMsg, setResultMsg] = useState("");
  
  const saveGameMutation = useSaveGame();

  // Handle game end
  const handleGameOver = useCallback((reason: string, resultCode: string) => {
    if (gameOver) return;
    setGameOver(true);
    setResultMsg(reason);
    
    saveGameMutation.mutate({
      player1: p1,
      player2: p2,
      mode: mode,
      result: resultCode,
      pgn: game.pgn() || "No moves made",
    }, {
      onSuccess: () => {
        toast({
          title: "Match Terminated",
          description: "Data log saved to archives successfully.",
        });
      },
    });
  }, [game, gameOver, mode, p1, p2, saveGameMutation, toast]);

  // Check game status after every move
  useEffect(() => {
    if (game.isCheckmate()) {
      const winner = game.turn() === "w" ? p2 : p1;
      const resultCode = game.turn() === "w" ? "0-1" : "1-0";
      handleGameOver(`CHECKMATE: ${winner} wins`, resultCode);
    } else if (game.isDraw()) {
      let reason = "DRAW";
      if (game.isStalemate()) reason = "DRAW BY STALEMATE";
      if (game.isThreefoldRepetition()) reason = "DRAW BY REPETITION";
      handleGameOver(reason, "1/2-1/2");
    }
  }, [game, handleGameOver, p1, p2]);

  // AI Turn handler
  useEffect(() => {
    if (gameOver) return;

    const isWhiteTurn = game.turn() === 'w';
    let isAITurn = false;

    if (mode === 'ava') {
      isAITurn = true;
    } else if (mode === 'pva' && !isWhiteTurn) {
      isAITurn = true;
    }

    if (isAITurn) {
      const timer = setTimeout(() => {
        const aiMoveSan = makeAIMove(game);
        if (aiMoveSan) {
          const gameCopy = new Chess(game.fen());
          gameCopy.move(aiMoveSan);
          setGame(gameCopy);
        }
      }, 600); // Artificial delay for effect
      return () => clearTimeout(timer);
    }
  }, [game, mode, gameOver]);

  // Player move handler for 3D board
  const onMove = (source: string, target: string) => {
    if (gameOver) return;
    
    // Prevent human from moving AI pieces
    const isWhiteTurn = game.turn() === 'w';
    if (mode === 'ava') return;
    if (mode === 'pva' && !isWhiteTurn) return;

    const gameCopy = new Chess(game.fen());
    try {
      const move = gameCopy.move({
        from: source,
        to: target,
        promotion: "q", // Default promotion for simplicity in 3D
      });
      if (move) {
        setGame(gameCopy);
      }
    } catch (e) {
      // Invalid move
    }
  };

  const handleResign = () => {
    const winner = game.turn() === "w" ? p2 : p1;
    const resultCode = game.turn() === "w" ? "0-1" : "1-0";
    handleGameOver(`RESIGNATION: ${winner} wins`, resultCode);
  };

  return (
    <Layout>
      <div className="flex items-center gap-4 mb-6">
        <button 
          onClick={() => setLocation('/')}
          className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 font-display uppercase tracking-wider text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Abort_Match
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 w-full max-w-5xl mx-auto">
        
        {/* Main Board Area */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          
          {/* Opponent Info (Black) */}
          <div className="flex items-center justify-between bg-card/50 p-3 border border-secondary/30 rounded">
            <div className="flex items-center gap-3">
              {mode === 'pvp' ? <User className="text-secondary" /> : <Cpu className="text-secondary" />}
              <span className="font-display font-bold tracking-widest text-secondary text-glow-pink">
                {p2}
              </span>
            </div>
            {!gameOver && game.turn() === 'b' && (
              <span className="text-xs font-mono text-secondary animate-pulse">PROCESSING...</span>
            )}
          </div>

          {/* Cyber 3D Board Container */}
          <div className="cyber-board mx-auto w-full max-w-[600px] aspect-square p-2 bg-black/40 border border-primary/20 rounded-lg overflow-hidden touch-none">
            <Canvas shadows dpr={[1, 2]}>
              <PerspectiveCamera makeDefault position={[3.5, -4, 8]} fov={45} />
              <Suspense fallback={null}>
                <Board3D 
                  game={game} 
                  onMove={onMove} 
                  orientation="white" 
                />
              </Suspense>
              <OrbitControls 
                enablePan={false}
                minPolarAngle={Math.PI / 6}
                maxPolarAngle={Math.PI / 2.2}
                target={[3.5, 3.5, 0]}
              />
            </Canvas>
          </div>

          {/* Player Info (White) */}
          <div className="flex items-center justify-between bg-card/50 p-3 border border-primary/30 rounded">
            <div className="flex items-center gap-3">
              {mode === 'ava' ? <Cpu className="text-primary" /> : <User className="text-primary" />}
              <span className="font-display font-bold tracking-widest text-primary text-glow">
                {p1}
              </span>
            </div>
            {!gameOver && game.turn() === 'w' && (
              <span className="text-xs font-mono text-primary animate-pulse">AWAITING_INPUT...</span>
            )}
          </div>

        </div>

        {/* Sidebar Status/History */}
        <div className="flex flex-col gap-6">
          <div className="bg-card/80 border border-primary/20 rounded p-6 h-[300px] flex flex-col">
            <h3 className="text-primary font-display border-b border-primary/20 pb-2 mb-4 uppercase tracking-widest">
              Match_Status
            </h3>
            
            {gameOver ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center gap-4 animate-in zoom-in duration-500">
                <div className="text-2xl font-bold text-accent drop-shadow-[0_0_8px_rgba(253,242,0,0.8)]">
                  {resultMsg}
                </div>
                <p className="text-sm text-muted-foreground">Log recorded to archives.</p>
                <CyberButton onClick={() => setLocation('/')} variant="ghost" className="mt-4">
                  New_Session
                </CyberButton>
              </div>
            ) : (
              <div className="flex-1 flex flex-col">
                <div className="flex-1 overflow-y-auto font-mono text-sm space-y-1 mb-4 text-muted-foreground pr-2">
                  {game.history().reduce((result: any[], move, index) => {
                    if (index % 2 === 0) result.push([move]);
                    else result[result.length - 1].push(move);
                    return result;
                  }, []).map((turn, i) => (
                    <div key={i} className="flex gap-4">
                      <span className="text-primary/50 w-6">{i + 1}.</span>
                      <span className="w-16 text-primary">{turn[0]}</span>
                      {turn[1] && <span className="w-16 text-secondary">{turn[1]}</span>}
                    </div>
                  ))}
                  {game.history().length === 0 && <span className="opacity-50">No moves executed yet.</span>}
                </div>
                
                <div className="mt-auto pt-4 border-t border-primary/20 flex gap-2">
                  <CyberButton onClick={handleResign} variant="secondary" className="w-full py-2 text-xs">
                    Resign
                  </CyberButton>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </Layout>
  );
}
