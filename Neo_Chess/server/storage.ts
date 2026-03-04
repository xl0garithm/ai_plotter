import { db } from "./db";
import { games, type InsertGame, type Game } from "@shared/schema";
import { desc } from "drizzle-orm";

export interface IStorage {
  createGame(game: InsertGame): Promise<Game>;
  getGames(): Promise<Game[]>;
}

export class DatabaseStorage implements IStorage {
  async createGame(insertGame: InsertGame): Promise<Game> {
    const [game] = await db.insert(games).values(insertGame).returning();
    return game;
  }

  async getGames(): Promise<Game[]> {
    // Return latest games first
    return await db.select().from(games).orderBy(desc(games.createdAt));
  }
}

export const storage = new DatabaseStorage();
