import { pgTable, text, serial, timestamp, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const games = pgTable("games", {
  id: serial("id").primaryKey(),
  playerName: text("player_name").notNull(),
  opponentName: text("opponent_name").notNull().default("CORTEX AI"),
  gameMode: text("game_mode").notNull().default("pvai"),
  winner: text("winner"),
  difficulty: text("difficulty").default("medium"),
  moves: integer("moves").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertGameSchema = createInsertSchema(games).omit({ id: true, createdAt: true });

export type Game = typeof games.$inferSelect;
export type InsertGame = z.infer<typeof insertGameSchema>;
