"""USB serial plotter controller."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, Optional

import serial


class PlotterError(RuntimeError):
    """Raised when plotter communication fails."""


class PlotterController:
    """Manage communication with the drawing plotter over USB serial."""

    def __init__(self, port: str, baudrate: int, *, timeout: float = 2.0, startup_delay: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.startup_delay = startup_delay
        self._serial: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Open the serial connection."""
        if self._serial and self._serial.is_open:
            return

        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except serial.SerialException as exc:
            raise PlotterError(f"Unable to connect to plotter on {self.port}: {exc}") from exc

        time.sleep(self.startup_delay)

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._serial:
            self._serial.close()
            self._serial = None

    def _ensure_connection(self) -> None:
        if not self._serial or not self._serial.is_open:
            raise PlotterError("Serial connection is not open.")

    def send_gcode_lines(self, lines: Iterable[str]) -> None:
        """Send G-code lines to the plotter."""
        self._ensure_connection()
        assert self._serial is not None  # for type checkers

        for line in lines:
            command = line.strip()
            if not command:
                continue
            payload = f"{command}\n".encode("utf-8")
            self._serial.write(payload)
            self._serial.flush()
            self._wait_for_ok()

    def send_gcode_file(self, file_path: Path) -> None:
        """Send a G-code file to the plotter."""
        if not file_path.exists():
            raise PlotterError(f"G-code file '{file_path}' not found.")
        with file_path.open("r", encoding="utf-8") as fp:
            lines = fp.readlines()
        self.send_gcode_lines(lines)

    def _wait_for_ok(self) -> None:
        """Wait for an OK response from the plotter."""
        assert self._serial is not None
        response = self._serial.readline().decode("utf-8").strip()
        if response and response.lower() != "ok":
            raise PlotterError(f"Unexpected response from plotter: {response}")

