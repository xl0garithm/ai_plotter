# Run from ai_plotter directory. Targets use .venv/bin/python — no shell activation needed
# (works when running as root on Raspberry Pi without sourcing activate).
HOST_PYTHON ?= python3
VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: test lint fmt setup venv setup-prod _venv_ok

_venv_ok:
	@test -f "$(PY)" || (echo "Missing .venv. Run: make setup (dev) or make setup-prod (runtime only)" >&2 && exit 1)

venv:
	@test -d "$(VENV)" || "$(HOST_PYTHON)" -m venv "$(VENV)"
	"$(PIP)" install -U pip
	"$(PIP)" install -r requirements-dev.txt

setup: venv

setup-prod:
	@test -d "$(VENV)" || "$(HOST_PYTHON)" -m venv "$(VENV)"
	"$(PIP)" install -U pip
	"$(PIP)" install -r requirements.txt

test: _venv_ok
	cd "$(CURDIR)" && "$(PY)" -m pytest

lint: _venv_ok
	"$(PY)" -m ruff check . tests
	"$(PY)" -m ruff format --check .

fmt: _venv_ok
	"$(PY)" -m ruff format .
	"$(PY)" -m ruff check --fix .
