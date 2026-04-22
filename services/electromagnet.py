"""Raspberry Pi electromagnet control via PWM (host-side; not sent as G-code)."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# Host-only directives embedded in G-code streams; PlotterController strips them.
MAGNET_GCODE_ON = "; @MAGNET_ON"
MAGNET_GCODE_OFF = "; @MAGNET_OFF"


class ElectromagnetBase:
    """Abstract electromagnet: full-on PWM or off."""

    def full_on(self) -> None:
        raise NotImplementedError

    def off(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class NoOpElectromagnet(ElectromagnetBase):
    """No hardware; safe on laptops and CI."""

    def full_on(self) -> None:
        logger.debug("Electromagnet (noop): full_on")

    def off(self) -> None:
        logger.debug("Electromagnet (noop): off")

    def close(self) -> None:
        pass


class PWMElectromagnet(ElectromagnetBase):
    """PWM on a BCM GPIO pin (e.g. 12) via gpiozero.

    The Pi pin only supplies **logic-level** PWM (3.3 V, low current). The electromagnet coil must
    be switched from the **board supply** (e.g. 5 V / 12 V) through a MOSFET or driver; this class
    does not measure coil current. ``pwm_on_value`` sets :attr:`PWMOutputDevice.value` when on
    (0.0–1.0 duty) to control average **input** power to the gate driver, not the coil directly.
    """

    def __init__(self, bcm_pin: int, frequency_hz: float, *, pwm_on_value: float = 1.0) -> None:
        from gpiozero import PWMOutputDevice

        self._pin = bcm_pin
        self._pwm_on = max(0.0, min(1.0, float(pwm_on_value)))
        self._dev: Any = PWMOutputDevice(bcm_pin, frequency=frequency_hz)
        self._dev.value = 0.0

    def full_on(self) -> None:
        self._dev.value = self._pwm_on
        logger.info(
            "Electromagnet: PWM on (pin BCM %s, duty=%.3f)",
            self._pin,
            self._pwm_on,
        )

    def off(self) -> None:
        self._dev.value = 0.0
        logger.info("Electromagnet: off (pin BCM %s)", self._pin)

    def close(self) -> None:
        try:
            self.off()
            self._dev.close()
        except Exception:
            logger.debug("Electromagnet close failed", exc_info=True)


def create_electromagnet(
    *,
    enabled: bool,
    bcm_pin: int = 12,
    frequency_hz: float = 1000.0,
    pwm_on_value: float = 1.0,
) -> ElectromagnetBase:
    """Build a real PWM electromagnet or a no-op when disabled or GPIO is unavailable."""
    if not enabled:
        return NoOpElectromagnet()
    try:
        return PWMElectromagnet(bcm_pin, frequency_hz, pwm_on_value=pwm_on_value)
    except Exception as exc:
        logger.warning("Electromagnet GPIO not available (%s); using no-op.", exc)
        return NoOpElectromagnet()


def create_electromagnet_from_mapping(config: Mapping[str, Any]) -> ElectromagnetBase:
    """Create from Flask ``app.config`` or any dict-like with the same keys as ``Config``."""
    enabled = bool(config.get("ELECTROMAGNET_ENABLED", False))
    pin = int(config.get("ELECTROMAGNET_BCM_PIN", 12))
    freq = float(config.get("ELECTROMAGNET_PWM_FREQUENCY_HZ", 1000.0))
    duty = float(config.get("ELECTROMAGNET_PWM_VALUE", 1.0))
    duty = max(0.0, min(1.0, duty))
    return create_electromagnet(
        enabled=enabled,
        bcm_pin=pin,
        frequency_hz=freq,
        pwm_on_value=duty,
    )


def parse_magnet_directive(line: str) -> Optional[str]:
    """Return ``\"on\"``, ``\"off\"``, or ``None`` for host-only magnet lines."""
    raw = line.strip()
    if not raw:
        return None
    if raw.startswith(";"):
        inner = raw[1:].strip()
    else:
        inner = raw
    if inner.upper() == "@MAGNET_ON":
        return "on"
    if inner.upper() == "@MAGNET_OFF":
        return "off"
    return None
