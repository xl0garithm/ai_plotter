import { Link } from "wouter";
import { AlertTriangle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background p-4">
      <div className="glass-panel p-12 text-center max-w-md w-full border-destructive/50">
        <AlertTriangle className="w-16 h-16 text-destructive mx-auto mb-6" />
        <h1 className="text-4xl font-black text-white mb-2 tracking-widest">404</h1>
        <p className="text-destructive font-mono uppercase tracking-widest mb-8">
          SECTOR NOT FOUND
        </p>
        <Link href="/" className="inline-block px-8 py-3 bg-destructive/10 border border-destructive text-destructive hover:bg-destructive hover:text-white transition-colors uppercase font-bold tracking-widest">
          RETURN TO BASE
        </Link>
      </div>
    </div>
  );
}
