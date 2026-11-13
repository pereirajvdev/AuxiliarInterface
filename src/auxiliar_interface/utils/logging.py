"""Logging da biblioteca (usa o logger ``auxiliar_interface``)."""

from __future__ import annotations

import logging as _logging
import sys
from typing import TextIO

LOGGER_NAME = "auxiliar_interface"

_logging.getLogger(LOGGER_NAME).addHandler(_logging.NullHandler())


def get_logger(name: str | None = None) -> _logging.Logger:
    """Retorna o logger da biblioteca (ou um filho dele)."""
    return _logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


def configure_logging(verbosity: int = 0, stream: TextIO | None = None) -> None:
    """Configura saída de log: 0=WARNING, 1=INFO, 2+=DEBUG."""
    level = {0: _logging.WARNING, 1: _logging.INFO}.get(verbosity, _logging.DEBUG)
    logger = _logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        if getattr(handler, "_auxiliar_cli", False):
            logger.removeHandler(handler)
    handler = _logging.StreamHandler(stream or sys.stderr)
    handler._auxiliar_cli = True  # type: ignore[attr-defined]
    handler.setFormatter(_logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
