# NeoChess

## Overview

NeoChess is a cyberpunk-themed chess game built as a frontend-only TypeScript application. Players can compete in three modes: Player vs Player, Player vs AI, or watch AI vs AI. The game features a futuristic neon 3D aesthetic with animations. Game history is stored in localStorage.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight React router)
- **State Management**: React hooks for local state
- **Styling**: Tailwind CSS with custom cyberpunk theme using CSS variables
- **UI Components**: shadcn/ui component library (New York style variant)
- **Animations**: Framer Motion for board animations and transitions
- **3D Rendering**: React Three Fiber + Three.js for 3D chess board and pieces
- **Special Effects**: canvas-confetti for victory celebrations

### Game Logic
- **Chess Library**: chess.js — handles all chess rules, move generation, validation, check/checkmate/draw detection
- **AI Engine**: Custom minimax with alpha-beta pruning and piece-square tables
- **AI Difficulty**: easy (random + captures), medium (depth 2), hard (depth 3)
- **Game Modes**: PvP (both human), PvAI (white=human, black=AI), AIvAI (both AI)
- **Pawn Promotion**: Handled via modal dialog, choice of Q/R/B/N

The frontend follows a pages-based structure with three main routes:
- Home (`/`) - Player setup, mode selection, difficulty
- Game (`/game`) - Main 3D gameplay board
- History (`/history`) - Past game records from localStorage

### Backend Architecture
- **Runtime**: Node.js with Express
- **Language**: TypeScript (ESM modules)
- **Build Tool**: Vite for development, esbuild for production bundling
- The backend is minimal — the game is entirely frontend-only

### Data Storage
- **Game History**: localStorage (`neo_chess_history`) — stores up to 50 game records
- **Schema**: shared/schema.ts defines the game structure with playerName, opponentName, gameMode, winner, difficulty, moves fields

### 3D Chess Board (Board.tsx)
- 8x8 board rendered with React Three Fiber
- Distinct 3D piece models for each chess piece type using Three.js primitives
- Cyan (white) vs Magenta (black) neon cyberpunk color scheme
- Pieces animate with spring physics when moving
- Jump arc animation on piece movement
- Valid move squares highlighted in green
- Last move squares highlighted in yellow
- King in check highlighted in red
- Selection glow effect on selected piece

### Key Files
- `client/src/hooks/use-chess-engine.ts` — Main game logic, AI, chess.js integration
- `client/src/components/Board.tsx` — 3D chess board renderer
- `client/src/pages/Home.tsx` — Start screen with mode/difficulty selection
- `client/src/pages/Game.tsx` — Game HUD, captured pieces, game over modal
- `client/src/pages/History.tsx` — Archive of past games
- `shared/schema.ts` — Game record schema

## External Dependencies

### Chess
- **chess.js**: Chess game logic, move validation, rule enforcement

### Frontend Libraries
- **React Three Fiber**: 3D rendering in React
- **Three.js / @react-three/drei**: 3D utilities and controls
- **Framer Motion**: Animation library
- **canvas-confetti**: Particle effects for victory
- **date-fns**: Date formatting in history
- **Lucide React**: Icon library

### Development Tools
- **Vite**: Development server with HMR
- **TypeScript**: Strict mode with bundler module resolution
