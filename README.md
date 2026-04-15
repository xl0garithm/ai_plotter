# Chess Plotter

FastAPI app for playing chess (human vs human, human vs computer, computer vs computer) and driving an XY plotter over USB serial. Chess runs fully offline.

## Features

- **Chess play** at `/chess` (Neo_Chess): React SPA with in-browser AI, optional execute-on-plotter.
- **Chess (Legacy)** at `/chess-legacy`: Stockfish backend, three modes, difficulty levels, UCI moves, execute-on-plotter.
- **Admin queue** at `/admin`: manual upload of outline images, approve, print to plotter.
- Vectorization and G-code pipeline for the plotter; USB serial driver.

## Prerequisites

- Python 3.10+
- Node.js (for Neo_Chess build)
- Serial port for plotter (e.g. `/dev/ttyUSB0`, `COM3`)
- Stockfish binary (on `PATH` or set `STOCKFISH_PATH`) — for `/chess-legacy` only

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build Neo_Chess front-end (required for /chess)
cd Neo_Chess && npm install && npx vite build && cd ..
```

Copy `env.example` to `.env`. Main variables:

- `FLASK_SECRET_KEY` – session secret
- `PLOTTER_SERIAL_PORT` – plotter serial port
- `PLOTTER_BAUDRATE` – default `115200`
- `PLOTTER_DRY_RUN` – if `true`, no serial output; G-code written to `.dryrun.txt`
- `STOCKFISH_PATH` – optional path to Stockfish binary (for `/chess-legacy`)

## Run

```bash
# Option 1: app.py (port 5000, reload)
python app.py

# Option 2: uvicorn directly (default port 8000)
uvicorn main:app --reload --host 0.0.0.0
```

- `http://localhost:5000/` or `http://localhost:8000/` – home (links to Play Chess, Chess Legacy, Admin)
- `http://localhost:5000/chess/` – Neo_Chess (React, in-browser AI)
- `http://localhost:5000/chess-legacy` – Legacy chess (Stockfish backend)
- `http://localhost:5000/admin/` – queue and print control

If port 8000 is in use: run `fuser -k 8000/tcp` to free it, or use `--port 8001` and open http://localhost:8001/ instead.

## Testing and linting

Run from the `ai_plotter` directory with the virtualenv activated.

**Tests**

```bash
pytest
# or
make test
```

Tests use in-memory SQLite and mock the plotter; no serial port or `PLOTTER_DRY_RUN` is required for the test suite.

**Lint and format**

```bash
# Check only (CI)
make lint

# Fix and format
make fmt
```

Requires dev dependencies: `pip install -r requirements-dev.txt` (adds `ruff`).

- `make lint` — ruff check + format check  
- `make fmt` — ruff format + ruff check --fix

## Chess robot: physical assumptions

When using execute-on-plotter for chess, the following physical assumptions apply:

- **Pieces:** Same height is assumed so that a lifted piece clears the board; there is no per-piece or per-type logic. If pieces differ in height (e.g. king vs pawn), tall pieces may collide during travel—use uniform piece height or verify clearance manually.
- **Clearance:** Chess G-code does not set Z/lift height; the magnet operates at a single height. Ensure the physical setup provides enough clearance for the tallest piece when moving.
- **Board and origin:** The physical board must match `CHESS_BOARD_SIZE_MM`, `CHESS_SQUARE_COUNT`, and `CHESS_ORIGIN_X_MM` / `CHESS_ORIGIN_Y_MM`. Optionally use `CHESS_DIMENSIONS_JSON` (see env.example) to load dimensions from a CAD export.
- **Discard:** Captured pieces are moved to a discard position at `origin - 1.5 * square_size` in X and Y. Ensure this is off the board and the path is clear.
- **Magnet timing:** The electromagnet stays on from pickup until after place (the whole move). Longest move duration is roughly travel distance divided by rapid feed rate. If your controller has a maximum magnet on-time, set `CHESS_RAPID_FEED_MM_S` and optionally `CHESS_MAGNET_MAX_ON_S` so the app can warn when a move would exceed it.
- **Castling:** The plotter runs **two** motions (king, then rook). Only standard O-O / O-O-O start squares are supported (`e1g1`+`h1f1`, etc.).
- **En passant:** Neo_Chess sends `captured_square` on `POST /api/chess/execute-move` so the captured pawn is lifted from the correct square (not the landing square).
- **Promotion:** The magnet moves the pawn to the promotion square; swapping in a physical queen/rook/bishop/knight is still manual unless you extend the hardware flow.
