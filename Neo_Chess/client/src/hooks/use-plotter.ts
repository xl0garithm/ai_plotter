import { useState, useCallback } from "react";
import { api } from "@shared/routes";

export interface PlotterStats {
  from: string;
  to: string;
  piece: string;
  flags: string;
  captured: string | null;
  phases: number;
  gcode_lines: number;
}

export interface PlotterResult {
  success: boolean;
  dry_run?: boolean;
  stats: PlotterStats;
  gcode_lines?: string[];
}

export function usePlotter() {
  const [isPrinting, setIsPrinting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PlotterResult | null>(null);

  const executeMove = useCallback(async (move: {
    from: string;
    to: string;
    piece: string;
    color: "w" | "b";
    flags?: string;
    captured?: string | null;
    promotion?: string | null;
    capture_index?: number;
  }): Promise<PlotterResult | null> => {
    console.log("[PLOTTER] executeMove called:", move);
    setIsPrinting(true);
    setError(null);

    try {
      console.log("[PLOTTER] Sending request to:", api.chess.move.path);
      const response = await fetch(api.chess.move.path, {
        method: api.chess.move.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from: move.from,
          to: move.to,
          piece: move.piece,
          color: move.color,
          flags: move.flags || "",
          captured: move.captured || null,
          promotion: move.promotion || null,
          capture_index: move.capture_index || 0,
        }),
      });

      const data = await response.json();
      console.log("[PLOTTER] Response:", response.status, data);
      
      if (!response.ok) {
        throw new Error(data.message || "Failed to execute move");
      }

      setLastResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("[PLOTTER] Error:", message);
      setError(message);
      return null;
    } finally {
      setIsPrinting(false);
    }
  }, []);

  const runDemo = useCallback(async (): Promise<PlotterResult | null> => {
    setIsPrinting(true);
    setError(null);

    try {
      const response = await fetch(api.chess.demoRun.path, {
        method: api.chess.demoRun.method,
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || "Failed to run demo");
      }

      setLastResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      return null;
    } finally {
      setIsPrinting(false);
    }
  }, []);

  const runPickPlaceDemo = useCallback(async (from = "e2", to = "e4"): Promise<PlotterResult | null> => {
    setIsPrinting(true);
    setError(null);

    try {
      const response = await fetch(api.chess.pickPlaceDemo.path, {
        method: api.chess.pickPlaceDemo.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from, to }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || "Failed to run pick-place demo");
      }

      setLastResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      return null;
    } finally {
      setIsPrinting(false);
    }
  }, []);

  const getPreview = useCallback(async (): Promise<string | null> => {
    try {
      const response = await fetch(`${api.chess.preview.path}?size=800&hatch_spacing=6.0`);
      if (!response.ok) return null;
      return await response.text();
    } catch {
      return null;
    }
  }, []);

  return {
    isPrinting,
    error,
    lastResult,
    executeMove,
    runDemo,
    runPickPlaceDemo,
    getPreview,
  };
}
