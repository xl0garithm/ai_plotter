import { useState } from "react";
import { useLocation } from "wouter";
import { Layout } from "@/components/layout";
import { CyberButton } from "@/components/cyber-button";
import { CyberInput } from "@/components/cyber-input";
import { Cpu, Users, Bot } from "lucide-react";

type Mode = "pvp" | "pva" | "ava";

export default function Home() {
  const [, setLocation] = useLocation();
  const [mode, setMode] = useState<Mode>("pva");
  const [player1, setPlayer1] = useState("Player 1");
  const [player2, setPlayer2] = useState("Player 2");

  const handleStart = () => {
    const params = new URLSearchParams({
      mode,
      p1: mode === "ava" ? "AI_1" : player1 || "Anonymous",
      p2: mode === "pvp" ? (player2 || "Anonymous 2") : "AI_Omega"
    });
    setLocation(`/play?${params.toString()}`);
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full">
        
        <div className="text-center mb-12">
          <h1 className="text-5xl md:text-7xl font-bold text-glow mb-4 tracking-[0.2em]">
            NEON<span className="text-secondary text-glow-pink">CHESS</span>
          </h1>
          <p className="text-muted-foreground font-mono crt-flicker">
            Initialize combat sequence. Awaiting parameters...
          </p>
        </div>

        <div className="w-full bg-card/60 backdrop-blur-sm border border-primary/30 p-8 rounded-lg relative overflow-hidden">
          {/* Decorative frame corners */}
          <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary" />
          <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary" />
          <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary" />
          <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary" />

          <h2 className="text-xl mb-6 text-primary border-b border-primary/20 pb-2">Select_Protocol</h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <button
              onClick={() => setMode("pvp")}
              className={`flex flex-col items-center gap-3 p-4 border-2 transition-all duration-300 ${
                mode === "pvp" 
                  ? "border-primary bg-primary/10 box-glow" 
                  : "border-muted-foreground/30 hover:border-primary/50 bg-background/50"
              }`}
            >
              <Users className={`w-8 h-8 ${mode === "pvp" ? "text-primary" : "text-muted-foreground"}`} />
              <span className="font-display tracking-widest font-bold">PvP</span>
            </button>
            
            <button
              onClick={() => setMode("pva")}
              className={`flex flex-col items-center gap-3 p-4 border-2 transition-all duration-300 ${
                mode === "pva" 
                  ? "border-secondary bg-secondary/10 box-glow-pink" 
                  : "border-muted-foreground/30 hover:border-secondary/50 bg-background/50"
              }`}
            >
              <div className="flex gap-1">
                <Users className={`w-6 h-6 ${mode === "pva" ? "text-primary" : "text-muted-foreground"}`} />
                <span className="text-muted-foreground">vs</span>
                <Cpu className={`w-6 h-6 ${mode === "pva" ? "text-secondary" : "text-muted-foreground"}`} />
              </div>
              <span className="font-display tracking-widest font-bold">PvE</span>
            </button>
            
            <button
              onClick={() => setMode("ava")}
              className={`flex flex-col items-center gap-3 p-4 border-2 transition-all duration-300 ${
                mode === "ava" 
                  ? "border-accent bg-accent/10 shadow-[0_0_15px_rgba(253,242,0,0.3)]" 
                  : "border-muted-foreground/30 hover:border-accent/50 bg-background/50"
              }`}
            >
              <Bot className={`w-8 h-8 ${mode === "ava" ? "text-accent" : "text-muted-foreground"}`} />
              <span className="font-display tracking-widest font-bold">EvE</span>
            </button>
          </div>

          <div className="space-y-6 mb-10">
            {(mode === "pvp" || mode === "pva") && (
              <div className="animate-in fade-in slide-in-from-top-4 duration-300">
                <CyberInput 
                  label="Player_1_ID (White)" 
                  value={player1}
                  onChange={(e) => setPlayer1(e.target.value)}
                  placeholder="Enter designation..."
                />
              </div>
            )}
            
            {mode === "pvp" && (
              <div className="animate-in fade-in slide-in-from-top-4 duration-300">
                <CyberInput 
                  label="Player_2_ID (Black)" 
                  value={player2}
                  onChange={(e) => setPlayer2(e.target.value)}
                  placeholder="Enter designation..."
                />
              </div>
            )}
          </div>

          <div className="flex justify-center">
            <CyberButton 
              onClick={handleStart} 
              variant={mode === "pva" ? "secondary" : "primary"}
              className="w-full sm:w-auto min-w-[200px]"
            >
              Execute_Sequence
            </CyberButton>
          </div>
        </div>
      </div>
    </Layout>
  );
}
