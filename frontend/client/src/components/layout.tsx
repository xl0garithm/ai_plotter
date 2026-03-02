import { ReactNode } from "react";
import { Link } from "wouter";
import { Terminal } from "lucide-react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="cyber-grid" />
      <div className="crt-overlay" />
      
      <div className="min-h-screen flex flex-col relative z-10">
        <header className="border-b border-primary/30 bg-background/80 backdrop-blur-md sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group cursor-pointer">
              <Terminal className="w-6 h-6 text-primary group-hover:text-secondary transition-colors" />
              <span className="font-display font-bold text-xl tracking-widest text-glow">NEON_CHESS</span>
            </Link>
            
            <nav className="flex gap-6">
              <Link href="/" className="font-display font-semibold uppercase tracking-widest text-sm text-muted-foreground hover:text-primary transition-colors cursor-pointer">
                System_Boot
              </Link>
              <Link href="/archives" className="font-display font-semibold uppercase tracking-widest text-sm text-muted-foreground hover:text-secondary transition-colors cursor-pointer">
                Data_Logs
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1 flex flex-col max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </>
  );
}
