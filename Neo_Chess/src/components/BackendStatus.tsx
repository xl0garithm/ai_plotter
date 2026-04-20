import { useCallback, useEffect, useState } from "react";

type BackendState = "checking" | "online" | "offline";

export function BackendStatus() {
  const [status, setStatus] = useState<BackendState>("checking");

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/health", {
        method: "GET",
        cache: "no-store",
      });
      setStatus(res.ok ? "online" : "offline");
    } catch {
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const intervalId = window.setInterval(checkHealth, 10000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [checkHealth]);

  const dotClass =
    status === "online"
      ? "bg-primary shadow-[0_0_10px_rgba(0,243,255,0.9)]"
      : status === "checking"
        ? "bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.9)]"
        : "bg-destructive shadow-[0_0_10px_rgba(255,0,0,0.85)]";

  const label =
    status === "online"
      ? "Backend Online"
      : status === "checking"
        ? "Backend Checking"
        : "Backend Offline";

  return (
    <div className="fixed left-4 top-4 z-50 flex items-center gap-2 rounded-full border border-primary/30 bg-background/85 px-3 py-1.5 backdrop-blur-md">
      <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} />
      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-foreground">{label}</span>
    </div>
  );
}
