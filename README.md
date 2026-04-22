# AI Caricature Plotter + Chess robot

Flask application for capturing webcam images, generating AI caricatures (Gemini), plotting on an XY machine over USB serial, and—on the **`chess_gtm`** branch—driving a physical chess board with G-code plus optional **Raspberry Pi GPIO** control of an electromagnet.

## Features

- **Caricature pipeline** at `/`: capture, Gemini generation, vectorization, admin queue, print to plotter.
- **Admin** at `/admin/`: job approval, manual upload, print control.
- **Chess (plotter)** at `/chess`: board preview / plotter-oriented UI (Jinja template).
- **Neo_Chess** (React): 3D board, local AI, and `POST /api/chess/move` to the robot when enabled—run via Vite in dev (proxies `/api` to Flask) or build static assets for your reverse proxy (see below).
- **REST API** under `/api/`: jobs, chess board SVG/G-code, `POST /api/chess/move` (verbose chess.js moves), `POST /api/chess/execute-move` (UCI or `from`/`to`), health, etc.

## Prerequisites

- Python 3.10+
- Node.js 20+ (for Neo_Chess; Vite may warn below 20.19—upgrade if needed)
- Gemini API key for caricature generation
- USB serial access to the plotter
- **Optional (physical chess):** Raspberry Pi (or compatible) with `gpiozero` if `ELECTROMAGNET_ENABLED=true`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Copy `env.example` to `.env` and adjust variables (see table below and **`env.example`**).

**Neo_Chess (optional):**

```bash
cd Neo_Chess && npm ci && npm run build && cd ..
```

Committed `Neo_Chess/dist` may already exist; rebuild after UI changes. For local dev with hot reload:

```bash
cd Neo_Chess && npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:5000`—run Flask on port 5000 in another terminal.

## Run

```bash
export FLASK_APP=app.py
flask run
```

- `http://127.0.0.1:5000/` — caricature capture UI  
- `http://127.0.0.1:5000/admin/` — admin  
- `http://127.0.0.1:5000/chess` — template chess UI  
- `http://127.0.0.1:5000/api/health` — health JSON  

Neo_Chess production URLs use base path `/chess/` (see `Neo_Chess/vite.config.ts`). Serve the Vite `dist` output under that path (e.g. nginx) in front of the same host as Flask, or use `npm run dev` during development.

## Environment variables (summary)

| Variable | Description |
|----------|-------------|
| `FLASK_SECRET_KEY` | Flask session secret |
| `GEMINI_API_KEY` | Gemini REST API key |
| `GEMINI_MODEL` | Model name (image-capable) |
| `PLOTTER_SERIAL_PORT` | Serial device (e.g. `/dev/ttyUSB0`, `COM3`) |
| `PLOTTER_BAUDRATE` | Default `115200` |
| `PLOTTER_DRY_RUN` | If true, skip serial; useful for tests and dry G-code |
| `CHESS_*` | Board geometry, gaps, dwells, capture tray, move feed—see `env.example` |
| `ELECTROMAGNET_*` | Pi GPIO magnet—see **GPIO section** below |

Full list and defaults: **`env.example`**.

## Raspberry Pi GPIO electromagnet (`chess_gtm`)

This branch can turn a **pick-and-place electromagnet** on and off from the Pi **in software**, while the XY plotter still receives normal G-code over serial. The Pi does **not** send PWM over the serial link; it toggles a **BCM GPIO pin** when the stream hits host-only directives.

### Hardware reality (read this first)

- GPIO pins are **3.3 V logic** and can only source/sink **small currents** (often on the order of ~8–16 mA per pin on many Pi models—check your board’s datasheet).
- **Do not** hang the magnet coil directly on a GPIO pin. Use a **low-side or high-side switch** (e.g. MOSFET + flyback diode) fed from the **same supply your magnet hardware expects** (e.g. 5 V or 12 V on your carrier board).
- The settings below control **PWM duty on the logic line** into that driver (`0.0`–`1.0`), not coil current directly. Lower duty reduces average drive into the gate network; it is **not** a substitute for proper current design on the load side.

### How it works in software

- G-code lines `; @MAGNET_ON` and `; @MAGNET_OFF` are **not** sent to the plotter. `PlotterController.send_gcode_lines(..., electromagnet=...)` consumes them and calls the electromagnet driver after the previous line ACKs.
- `services/electromagnet.py` uses **gpiozero** `PWMOutputDevice` on the configured BCM pin when `ELECTROMAGNET_ENABLED=true`. If GPIO is unavailable or disabled, a no-op driver is used (safe on laptops/CI).

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `ELECTROMAGNET_ENABLED` | `false` | Enable real GPIO when `true` |
| `ELECTROMAGNET_BCM_PIN` | `12` | BCM numbering (e.g. GPIO12) |
| `ELECTROMAGNET_PWM_FREQUENCY_HZ` | `1000` | PWM frequency |
| `ELECTROMAGNET_PWM_VALUE` | `1.0` | Duty when “on” (`0.0`–`1.0`) |

Chess move G-code also uses configurable `CHESS_MAGNET_ON_GCODE` / `CHESS_MAGNET_OFF_GCODE` for the **plotter** side where applicable; Pi PWM is independent of those strings.

### Neo_Chess and the backend

- `POST /api/chess/move` accepts verbose chess.js payloads (see `Neo_Chess/src/lib/physicalChessMove.ts`).
- Optional: `VITE_CHESS_API_BASE` (e.g. `http://127.0.0.1:5000`) and `VITE_ENABLE_PHYSICAL_CHESS=false` to disable robot POSTs from the SPA.

## Tests

```bash
pytest
```

Uses in-memory SQLite and mocked serial; no hardware required for the default suite.

## Chess robot: physical assumptions

- **Pieces:** Uniform height is assumed so a lifted piece clears the board; no per-piece Z logic.
- **Clearance:** Magnet operates at one height; verify tallest piece clearance on your machine.
- **Board:** Match `CHESS_BOARD_SIZE_MM`, `CHESS_SQUARE_COUNT`, `CHESS_GAP_MM`, and origins in `.env` to the real board.
- **Captures:** Discards use `CHESS_CAPTURE_*` and `capture_index` from the API; ensure the capture tray coordinates are reachable.
- **Castling:** Implemented as two physical legs (king, then rook) for UCI-style `execute-move`.
- **En passant:** For `POST /api/chess/execute-move` with UCI, pass `captured_square` so the victim square is correct.
- **Promotion:** Software moves the pawn to the last rank; swapping a physical promoted piece is still manual unless you extend the workflow.
