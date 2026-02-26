# CLAUDE.md

Guidance for working with this repository (chess_gtm branch: chess only, no caricature/Gemini). App is **FastAPI** (not Flask).

## Build and Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload
# or: python app.py

pytest
pytest tests/test_queue.py
pytest tests/test_queue.py::test_function_name -v
```

## Environment

Copy `env.example` to `.env`. Required:
- `PLOTTER_SERIAL_PORT` – serial port for XY plotter (e.g. `/dev/ttyUSB0`, `COM3`)

Optional: `PLOTTER_DRY_RUN=true` to skip serial and write G-code to `.dryrun.txt`.

Chess play (`/chess`) is fully offline: Stockfish + python-chess, no API key or internet. Set `STOCKFISH_PATH` if the engine is not on `PATH`.

## Architecture

FastAPI app: chess play (human/computer modes) and plotter job queue (manual upload → vectorize → G-code → serial).

- **Routers**: `routers/web.py` (pages, chess UI), `routers/admin.py` (auth, queue), `routers/api.py` (chess play API, queue/print endpoints). Admin auth via signed cookie (`dependencies.py`).
- **Services**: `queue.py` (job lifecycle, manual upload, print), `chess_game.py` (play session, Stockfish), `chess.py` (UCI→G-code), `vectorizer.py`, `gcode.py`, `plotter.py`, `database.py`.
- **Front end (chess play)**: [chess.js](https://github.com/jhlywa/chess.js) for browser move validation and FEN sync; backend remains python-chess + Stockfish.
- **Job flow**: manual upload → `generated` → `confirmed` → `approved` → `queued` → `printing` → `completed` (or `failed`/`cancelled`).

SQLite: `storage/app.db`. Storage under `storage/`: `uploads/`, `processed/`, `gcode/`.

## Known issues

- **Front-end vertical scroller on `/chess` is broken**: the chess page should show a vertical scrollbar when content exceeds the viewport; multiple layout/CSS fixes have been tried (body/scroll wrapper, inline styles, `min-height: 0` on main) but the scrollbar still does not appear in some environments. Needs further debugging (e.g. DevTools to confirm computed styles, test in different browsers).
