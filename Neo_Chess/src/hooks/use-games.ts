import type { InsertGame, StoredGame } from "@/types/game";

const STORAGE_KEY = "neo_chess_history";

export function useGames() {
  const gamesJson = localStorage.getItem(STORAGE_KEY);
  const games = gamesJson ? JSON.parse(gamesJson) : [];

  return {
    data: games as StoredGame[],
    isLoading: false,
    isError: false,
    refetch: () => {},
  };
}

export function useCreateGame() {
  return {
    mutate: (gameData: InsertGame) => {
      const gamesJson = localStorage.getItem(STORAGE_KEY);
      const games = gamesJson ? JSON.parse(gamesJson) : [];

      const newGame = {
        ...gameData,
        id: Date.now(),
        createdAt: new Date().toISOString(),
      };

      localStorage.setItem(STORAGE_KEY, JSON.stringify([newGame, ...games].slice(0, 50)));
    },
    isPending: false,
  };
}
