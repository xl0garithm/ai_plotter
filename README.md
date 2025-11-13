# AI Caricature Plotter

Python/Flask web application for capturing webcam images, generating AI caricatures via Gemini, and plotting them on an XY robot over USB serial.

## Features
- Browser UI with webcam preview, capture, retake, and submission flow.
- Gemini REST integration for caricature generation with manual confirmation step.
- Persistent job queue with admin dashboard for approval, cancellation, and print control.
- Automatic image scaling to 400×400 px and outline-to-G-code conversion.
- USB serial plotter driver that streams generated G-code to the robot.

## Prerequisites
- Python 3.10+
- Gemini API key (`GEMINI_API_KEY`)
- USB serial access to the plotter (e.g., `/dev/ttyUSB0`, `COM3`)
- Webcam accessible via browser (Chrome recommended)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate            # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Copy `env.example` to `.env` (or export these variables manually):

| Variable | Description |
| -------- | ----------- |
| `FLASK_SECRET_KEY` | Flask session secret |
| `GEMINI_API_KEY` | Gemini REST API key |
| `GEMINI_MODEL` | Gemini model name (default `gemini-2.0-flash-preview-image`, must support image output) |
| `PLOTTER_SERIAL_PORT` | Serial port for the plotter (`/dev/ttyUSB0`, `COM3`, etc.) |
| `PLOTTER_BAUDRATE` | Baud rate for the plotter (default `115200`) |
| `PLOTTER_SERIAL_TIMEOUT` | Serial read timeout seconds (default `2.0`) |
| `PLOTTER_DRY_RUN` | When `true`, skip serial output and dump G-code to `.dryrun.txt` |
| `PLOTTER_INVERT_Z` | Set `true` if your plotter lowers the pen with higher Z values |
| `PLOTTER_LINE_DELAY` | Extra seconds to wait between each streamed G-code line |

## Running
```bash
export FLASK_APP=app.py
flask run
```

Open `http://localhost:5000/` for the capture UI and `http://localhost:5000/admin/` for admin tools.

## Tests
```bash
pytest
```

