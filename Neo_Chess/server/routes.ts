import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://localhost:5001";

console.log(`[SERVER] Flask API URL: ${FLASK_API_URL}`);

async function proxyToFlask(req: Request, res: Response, next: NextFunction) {
  const path = req.originalUrl;
  const method = req.method;
  
  console.log(`[PROXY] ${method} ${path}`);
  if (method !== "GET" && req.body) {
    console.log(`[PROXY] Body:`, JSON.stringify(req.body, null, 2));
  }
  
  try {
    const url = `${FLASK_API_URL}${path}`;
    const fetchOptions: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    if (method !== "GET" && method !== "HEAD") {
      fetchOptions.body = JSON.stringify(req.body);
    }

    console.log(`[PROXY] Forwarding to: ${url}`);
    const response = await fetch(url, fetchOptions);
    const contentType = response.headers.get("content-type") || "";
    
    if (contentType.includes("image/svg")) {
      const svg = await response.text();
      console.log(`[PROXY] Received SVG response (${svg.length} bytes)`);
      res.set("Content-Type", "image/svg+xml");
      return res.send(svg);
    }
    
    const data = await response.json();
    console.log(`[PROXY] Response (${response.status}):`, JSON.stringify(data, null, 2).substring(0, 500));
    res.status(response.status).json(data);
  } catch (err) {
    console.error(`[PROXY] Error forwarding ${method} ${path}:`, err);
    res.status(502).json({ message: "Failed to reach ai_plotter API" });
  }
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  app.get(api.games.list.path, async (req, res) => {
    const games = await storage.getGames();
    res.json(games);
  });

  app.post(api.games.create.path, async (req, res) => {
    try {
      const input = api.games.create.input.parse(req.body);
      const game = await storage.createGame(input);
      res.status(201).json(game);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({
          message: err.errors[0].message,
          field: err.errors[0].path.join('.'),
        });
      }
      throw err;
    }
  });

  app.get(api.chess.preview.path, proxyToFlask);
  app.get(api.chess.demoPreview.path, proxyToFlask);
  app.post(api.chess.demoRun.path, proxyToFlask);
  app.post(api.chess.pickPlaceDemo.path, proxyToFlask);
  app.post(api.chess.move.path, proxyToFlask);

  // Direct test endpoint - doesn't need Flask
  app.get("/api/test", (req, res) => {
    console.log("[SERVER] Test endpoint hit!");
    res.json({ 
      status: "ok", 
      message: "Express server is working",
      flaskUrl: FLASK_API_URL,
      timestamp: new Date().toISOString()
    });
  });

  return httpServer;
}
