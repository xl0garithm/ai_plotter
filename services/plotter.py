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

    def __init__(
        self,
        port: str,
        baudrate: int,
        *,
        timeout: float = 10.0,
        startup_delay: float = 2.0,
        line_delay: float = 0.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.startup_delay = startup_delay
        self.line_delay = line_delay
        self._serial: Optional[serial.Serial] = None
        self._cancel_requested = False

    def connect(self) -> None:
        """Open the serial connection."""
        if self._serial and self._serial.is_open:
            return

        try:
            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        except serial.SerialException as exc:
            raise PlotterError(f"Unable to connect to plotter on {self.port}: {exc}") from exc

        time.sleep(self.startup_delay)
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()
        self._flush_startup()

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._serial:
            self._serial.close()
            self._serial = None
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Signal that the current streaming operation should stop."""
        self._cancel_requested = True

    def _ensure_connection(self) -> None:
        if not self._serial or not self._serial.is_open:
            raise PlotterError("Serial connection is not open.")

    def send_gcode_lines(self, lines: Iterable[str]) -> None:
        """Send G-code lines to the plotter."""
        self._ensure_connection()
        self._cancel_requested = False
        assert self._serial is not None  # for type checkers

        for idx, line in enumerate(lines, start=1):
            command = line.strip()
            if not command:
                continue
            if self._cancel_requested:
                raise PlotterError("Transmission cancelled by user.")
            payload = f"{command}\r\n".encode("utf-8")
            self._serial.write(payload)
            self._serial.flush()
            try:
                self._wait_for_ok()
            except PlotterError as exc:
                raise PlotterError(f"{exc} (line {idx}: '{command}')") from exc
            if self.line_delay > 0:
                time.sleep(self.line_delay)

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
        start_time = time.time()
        while True:
            response = self._serial.readline().decode("utf-8").strip().lower()
            if response == "ok":
                return
            if response in ("", None):
                if time.time() - start_time > self.timeout:
                    raise PlotterError("Timed out waiting for plotter OK response.")
                continue
            if response.startswith("error"):
                raise PlotterError(f"Plotter responded with error: {response}")
            # Ignore echoes and status messages, but guard against infinite loop
            if time.time() - start_time > self.timeout:
                raise PlotterError(f"Unexpected response from plotter: {response}")

    def _flush_startup(self) -> None:
        """Drain any startup banner lines."""
        assert self._serial is not None
        start = time.time()
        while time.time() - start < self.startup_delay:
            if not self._serial.in_waiting:
                break
            _ = self._serial.readline()

