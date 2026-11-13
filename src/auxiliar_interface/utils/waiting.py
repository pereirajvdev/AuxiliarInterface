"""Esperas com timeout configurável."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from ..exceptions import AutomationTimeoutError

T = TypeVar("T")


def wait_until(
    condition: Callable[[], T],
    *,
    timeout: float,
    interval: float = 0.1,
    description: str = "condição",
) -> T:
    """Repete ``condition`` até devolver um valor verdadeiro.

    A condição é avaliada ao menos uma vez, mesmo com ``timeout=0``.
    Levanta ``AutomationTimeoutError`` quando o prazo termina.
    """
    deadline = time.monotonic() + timeout
    while True:
        value = condition()
        if value:
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AutomationTimeoutError(
                f"Tempo esgotado ({timeout:g}s) aguardando: {description}"
            )
        time.sleep(min(interval, remaining))
