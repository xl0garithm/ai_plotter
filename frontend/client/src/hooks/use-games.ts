import { useState, useEffect } from "react";

export interface GameRecord {
  id: string;
  player1: string;
  player2: string;
  mode: string;
  result: string;
  pgn: string;
  createdAt: string;
}

const STORAGE_KEY = "chess_archives";

export function useGames() {
  const [games, setGames] = useState<GameRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setGames(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored games", e);
      }
    }
    setIsLoading(false);
  }, []);

  return { data: games, isLoading, error: null };
}

export function useSaveGame() {
  const mutate = (game: Omit<GameRecord, "id" | "createdAt">, options?: { onSuccess?: () => void }) => {
    const newGame: GameRecord = {
      ...game,
      id: Math.random().toString(36).substring(2, 9),
      createdAt: new Date().toISOString(),
    };

    const stored = localStorage.getItem(STORAGE_KEY);
    const games = stored ? JSON.parse(stored) : [];
    const updatedGames = [newGame, ...games];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedGames));

    if (options?.onSuccess) {
      options.onSuccess();
    }
  };

  return { mutate, isPending: false };
}
