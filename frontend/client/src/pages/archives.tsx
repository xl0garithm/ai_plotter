import { useLocation } from "wouter";
import { Layout } from "@/components/layout";
import { useGames } from "@/hooks/use-games";
import { ArrowLeft, Database, Trophy, Swords, Bot } from "lucide-react";
import { format } from "date-fns";

export default function Archives() {
  const [, setLocation] = useLocation();
  const { data: games, isLoading, error } = useGames();

  return (
    <Layout>
      <div className="flex items-center gap-4 mb-8">
        <button 
          onClick={() => setLocation('/')}
          className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 font-display uppercase tracking-wider text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Main_Menu
        </button>
      </div>

      <div className="mb-10">
        <h1 className="text-4xl font-bold font-display text-primary text-glow flex items-center gap-4 uppercase tracking-widest">
          <Database className="w-8 h-8" /> Data_Logs
        </h1>
        <p className="text-muted-foreground mt-2 font-mono">
          Retrieving historical combat records from main server...
        </p>
      </div>

      <div className="bg-card/40 border border-primary/20 rounded-lg overflow-hidden backdrop-blur-sm">
        {isLoading ? (
          <div className="p-12 text-center text-primary animate-pulse font-mono">
            Downloading records...
          </div>
        ) : error ? (
          <div className="p-12 text-center text-destructive font-mono">
            ERR_STORAGE: Failed to retrieve data logs.
          </div>
        ) : !games || games.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground font-mono">
            Local storage empty. No matches recorded.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-primary/10 border-b border-primary/30 text-primary font-display tracking-widest uppercase text-sm">
                  <th className="p-4 font-semibold">Timestamp</th>
                  <th className="p-4 font-semibold">Mode</th>
                  <th className="p-4 font-semibold">White (P1)</th>
                  <th className="p-4 font-semibold">Black (P2)</th>
                  <th className="p-4 font-semibold">Result</th>
                </tr>
              </thead>
              <tbody className="font-mono text-sm">
                {games.map((game) => (
                  <tr 
                    key={game.id} 
                    className="border-b border-primary/10 hover:bg-primary/5 transition-colors group"
                  >
                    <td className="p-4 text-muted-foreground">
                      {game.createdAt ? format(new Date(game.createdAt), "yyyy-MM-dd HH:mm") : "Unknown"}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 text-xs uppercase px-2 py-1 rounded border border-primary/30 w-fit">
                        {game.mode === 'pvp' && <Swords className="w-3 h-3 text-primary" />}
                        {game.mode === 'pva' && <span className="flex"><UserIcon className="w-3 h-3 text-primary"/><Bot className="w-3 h-3 text-secondary"/></span>}
                        {game.mode === 'ava' && <Bot className="w-3 h-3 text-accent" />}
                        <span className={
                          game.mode === 'pvp' ? "text-primary" : 
                          game.mode === 'pva' ? "text-secondary" : "text-accent"
                        }>{game.mode}</span>
                      </div>
                    </td>
                    <td className="p-4 font-bold text-foreground group-hover:text-primary transition-colors">
                      {game.player1}
                    </td>
                    <td className="p-4 font-bold text-foreground group-hover:text-secondary transition-colors">
                      {game.player2}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {game.result === '1-0' && <Trophy className="w-4 h-4 text-primary" />}
                        {game.result === '0-1' && <Trophy className="w-4 h-4 text-secondary" />}
                        <span className={`font-bold ${
                          game.result === '1-0' ? "text-primary" :
                          game.result === '0-1' ? "text-secondary" : "text-muted-foreground"
                        }`}>
                          {game.result}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}

// Simple internal helper to avoid missing import
function UserIcon(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinelinejoin="round" {...props}>
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
