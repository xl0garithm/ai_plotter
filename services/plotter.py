from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable, Optional

import serial

# ----- Exceptions -----
class PlotterError(RuntimeError):
    """Raised when plotter communication fails."""


# ----- Helper functions (from user-provided snippet, slightly adapted) -----
def _open_serial(port: str, baudrate: int, timeout: float) -> serial.Serial:
    """Open the serial port with the same settings used by the reference script."""
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baudrate
    ser.timeout = timeout  # read timeout (seconds)
    ser.write_timeout = timeout
    ser.open()
    return ser


def _wait_for_ack(ser: serial.Serial, ack: str, timeout: float) -> Optional[str]:
    """
    Read from *ser* until a line containing *ack* is seen or *timeout*
    seconds have elapsed. Matching is case-insensitive and whitespace-trimmed.
    Returns the matching line (stripped) or ``None`` on timeout.
    """
    deadline = time.time() + timeout
    buffer = b""
    ack_lc = ack.strip().lower()

    while time.time() < deadline:
        # read whatever is already waiting; fall back to a single byte poll
        try:
            chunk = ser.read(ser.in_waiting or 1)
        except Exception as exc:  # pragma: no cover – very unlikely
            logging.debug("Serial read error: %s", exc)
            return None

        if not chunk:
            # nothing received – give the CPU a breather
            time.sleep(0.01)
            continue

        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            try:
                txt = line.decode(errors="replace").strip()
            except Exception:  # pragma: no cover
                txt = repr(line)

            logging.debug("RX: %s", txt)
            if ack_lc in txt.lower():
                return txt

    # timeout
    return None


def _send_line_and_wait(
    ser: serial.Serial,
    line: str,
    ack: str,
    timeout: float,
    retries: int,
    send_delay: float = 0.0,
) -> bool:
    """
    Send *line* (ensuring a trailing newline) and wait for *ack*.
    Retries up to *retries* times. Returns ``True`` on success, ``False`` otherwise.
    """
    # Guarantee a line-terminator – the printer expects “\n”.
    encoded = line.encode("utf-8")
    if not (encoded.endswith(b"\n") or encoded.endswith(b"\r")):
        encoded += b"\n"

    attempt = 0
    while attempt <= retries:
        attempt += 1
        logging.info(
            "Sending (attempt %d/%d): %s", attempt, retries + 1, line.rstrip("\r\n")
        )
        try:
            ser.write(encoded)
            ser.flush()
        except Exception as exc:  # pragma: no cover – serial write failure is fatal
            logging.error("Failed to write to serial port: %s", exc)
            return False

        if send_delay:
            time.sleep(send_delay)

        resp = _wait_for_ack(ser, ack, timeout)
        if resp is not None:
            logging.info("ACK received: %s", resp)
            return True
        else:
            logging.warning(
                "No ACK within %.1f s (attempt %d/%d).", timeout, attempt, retries + 1
            )

    logging.error(
        "Exceeded %d retries without ACK for line: %s", retries, line.rstrip("\r\n")
    )
    return False


# ----- Main controller class -----
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
        send_retries: int = 2,
        ack: str = "ok",
    ):
        """
        Parameters
        ----------
        port, baudrate: as before
        timeout: read/write timeout passed to serial and ack wait (seconds)
        startup_delay: seconds to wait after opening port for device to settle
        line_delay: delay between lines (passed as send_delay to _send_line_and_wait)
        send_retries: number of retries for each line (0 means one attempt)
        ack: substring to match as acknowledgement (default 'ok')
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.startup_delay = startup_delay
        self.line_delay = line_delay
        self.send_retries = send_retries
        self.ack = ack

        self._serial: Optional[serial.Serial] = None
        self._cancel_requested = False

    # --- connection lifecycle ---
    def connect(self) -> None:
        """Open the serial connection using _open_serial and flush startup."""
        if self._serial and self._serial.is_open:
            return

        try:
            self._serial = _open_serial(self.port, self.baudrate, timeout=self.timeout)
        except serial.SerialException as exc:
            raise PlotterError(f"Unable to connect to plotter on {self.port}: {exc}") from exc

        # give the device time to boot and send any banner text
        time.sleep(self.startup_delay)
        try:
            # clear buffers like the original implementation
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except Exception:
            # Some backends don't implement reset_* methods; ignore non-fatal errors
            logging.debug("Serial reset buffer not available or failed", exc_info=True)

        self._flush_startup()

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                logging.debug("Error closing serial port", exc_info=True)
            finally:
                self._serial = None
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Signal that the current streaming operation should stop."""
        self._cancel_requested = True

    def _ensure_connection(self) -> None:
        if not self._serial or not self._serial.is_open:
            raise PlotterError("Serial connection is not open.")

    # --- sending G-code ---
    def send_gcode_lines(self, lines: Iterable[str]) -> None:
        """Send G-code lines to the plotter, using _send_line_and_wait for ACK handling."""
        self._ensure_connection()
        self._cancel_requested = False
        assert self._serial is not None  # for type checkers

        for idx, raw_line in enumerate(lines, start=1):
            # mirror behaviour of reference: strip CR/LF then re-append single LF
            line = raw_line.rstrip("\r\n") + "\n"
            if not line.strip():
                continue  # skip blank lines

            if self._cancel_requested:
                raise PlotterError("Transmission cancelled by user.")

            logging.info("SEND: %s", line.rstrip("\r\n"))
            ok = _send_line_and_wait(
                ser=self._serial,
                line=line,
                ack=self.ack,
                timeout=self.timeout,
                retries=self.send_retries,
                send_delay=self.line_delay,
            )
            if not ok:
                # add context about which line failed
                raise PlotterError(f"Failed to transmit line (line {idx}): {line.rstrip()}")

    def send_gcode_file(self, file_path: Path) -> None:
        """Send a G-code file to the plotter."""
        if not file_path.exists():
            raise PlotterError(f"G-code file '{file_path}' not found.")
        with file_path.open("r", encoding="utf-8") as fp:
            # stream lines directly to preserve memory characteristics
            self.send_gcode_lines(fp)

    # --- low-level helpers ---
    def _flush_startup(self) -> None:
        """Drain any startup banner lines (non-blocking)."""
        assert self._serial is not None
        start = time.time()
        # keep reading while there's data and we haven't exceeded startup_delay
        try:
            while time.time() - start < self.startup_delay:
                if not getattr(self._serial, "in_waiting", 0):
                    break
                _ = self._serial.readline()
        except Exception:
            # be tolerant: flushing is advisory
            logging.debug("Error while flushing startup banner", exc_info=True)