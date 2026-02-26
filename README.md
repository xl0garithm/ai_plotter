# Chess Plotter

FastAPI app for playing chess (human vs human, human vs computer, computer vs computer) and driving an XY plotter over USB serial. Chess runs fully offline (Stockfish + python-chess). The play UI uses [chess.js](https://github.com/jhlywa/chess.js) for client-side move validation and FEN sync; backend engine and state remain python-chess + Stockfish.

## Features

- Chess play at `/chess`: three modes, difficulty (Easy/Medium/Hard/Strongest via Stockfish Skill Level), UCI moves, optional execute-on-plotter.
- Admin queue at `/admin`: manual upload of outline images, approve, print to plotter.
- Vectorization and G-code pipeline for the plotter; USB serial driver.

## Prerequisites

- Python 3.10+
- Serial port for plotter (e.g. `/dev/ttyUSB0`, `COM3`)
- Stockfish binary (on `PATH` or set `STOCKFISH_PATH`)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `env.example` to `.env`. Main variables:

- `FLASK_SECRET_KEY` – session secret
- `PLOTTER_SERIAL_PORT` – plotter serial port
- `PLOTTER_BAUDRATE` – default `115200`
- `PLOTTER_DRY_RUN` – if `true`, no serial output; G-code written to `.dryrun.txt`
- `STOCKFISH_PATH` – optional path to Stockfish binary

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
# or: python app.py
```

- `http://localhost:5000/` – home (links to Play Chess and Admin)
- `http://localhost:5000/chess` – chess play
- `http://localhost:5000/admin/` – queue and print control

## Tests

```bash
pytest
```
