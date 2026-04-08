import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const games = sqliteTable("games", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  playerName: text("player_name").notNull(),
  opponentName: text("opponent_name").notNull().default("CORTEX AI"),
  gameMode: text("game_mode").notNull().default("pvai"),
  winner: text("winner"),
  difficulty: text("difficulty").default("medium"),
  moves: integer("moves").notNull(),
  createdAt: text("created_at").default(""),
});

export const insertGameSchema = createInsertSchema(games).omit({ id: true });

export type Game = typeof games.$inferSelect;
export type InsertGame = z.infer<typeof insertGameSchema>;
