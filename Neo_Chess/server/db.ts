import "dotenv/config";
import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import * as schema from "@shared/schema";

const dbPath = process.env.DATABASE_URL || "./storage/neo_chess.db";

const sqlite = new Database(dbPath);
export const db = drizzle(sqlite, { schema });
