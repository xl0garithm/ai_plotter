export type GameMode = "pvp" | "pvai" | "aivai";

export type GameDifficulty = "easy" | "medium" | "hard" | "pvp";

export type GameWinner = "white" | "black" | "draw";

export interface InsertGame {
  playerName: string;
  opponentName: string;
  gameMode: GameMode;
  winner: GameWinner;
  difficulty: GameDifficulty;
  moves: number;
}

export interface StoredGame extends InsertGame {
  id: number;
  createdAt: string;
}
