# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run development server
export FLASK_APP=app.py
flask run

# Run tests
pytest

# Run single test file
pytest tests/test_queue.py

# Run specific test
pytest tests/test_queue.py::test_function_name -v
```

## Environment Configuration

Copy `env.example` to `.env`. Required variables:
- `GEMINI_API_KEY` - Gemini REST API key for caricature generation
- `PLOTTER_SERIAL_PORT` - Serial port for the XY robot (e.g., `/dev/ttyUSB0`, `COM3`)

Set `PLOTTER_DRY_RUN=true` to skip serial output and dump G-code to `.dryrun.txt` files instead.

## Architecture Overview

This is a Flask application for generating AI caricatures and plotting them on an XY robot.

### Application Flow
1. User captures webcam image via browser UI (`/`)
2. Image is submitted to Gemini API for caricature generation
3. Generated image is vectorized (contours extracted, simplified, scaled)
4. Admin reviews and approves jobs (`/admin/`)
5. Approved jobs are converted to G-code and sent to plotter via serial

### Key Components

**Blueprints** (`blueprints/`):
- `web.py` - Serves HTML pages (capture UI, admin dashboard)
- `admin.py` - Admin authentication and views
- `api.py` - REST endpoints for job submission, approval, and printing

**Services** (`services/`):
- `queue.py` - Central job orchestration: creation, status transitions, print execution
- `gemini_client.py` - Gemini API wrapper for image generation
- `vectorizer.py` - Image-to-vector conversion using contour detection
- `gcode.py` - Vector-to-G-code conversion for the plotter
- `plotter.py` - Serial communication with the XY robot
- `database.py` - SQLAlchemy session management with `session_scope()` context manager

**Job Status Flow**:
`submitted` → `generating` → `generated` → `confirmed` → `approved` → `queued` → `printing` → `completed`

Jobs can transition to `failed` or `cancelled` from most states.

### Database

SQLite database at `storage/app.db`. Single `Job` model in `models.py` tracks all job state including paths to uploaded/generated images and G-code files.

### Storage Directories

All under `storage/`:
- `uploads/` - Original captured images
- `processed/` - Generated caricatures, SVG previews, vector JSON
- `gcode/` - Generated G-code files for plotter
