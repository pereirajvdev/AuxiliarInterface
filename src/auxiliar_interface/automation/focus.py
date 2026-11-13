"""Foco: consulta, espera por mudanças e política de ativação."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..core.locator import Criteria
from ..core.models import ElementInfo
from ..utils.logging import get_logger
from ..utils.waiting import wait_until

if TYPE_CHECKING:
    from ..core.context import Context

log = get_logger("focus")


@dataclass(frozen=True)
class FocusStep:
    """Resultado de um passo de ``trace_tab``."""

    step: int
    focus: ElementInfo | None


class FocusManager:
    """Consulta o controle com foco e garante a janela certa em primeiro plano."""

    def __init__(self, ctx: "Context") -> None:
        self._ctx = ctx

    def current(self) -> ElementInfo | None:
        """Controle com foco de teclado na thread em primeiro plano."""
        return self._ctx.backend.focused()

    def foreground_window(self) -> ElementInfo | None:
        return self._ctx.backend.foreground()

    def set(self, info: ElementInfo) -> bool:
        """Foca o elemento (traz a janela raiz ao primeiro plano se preciso)."""
        if not info.handle:
            log.debug("Elemento sem HWND; não é possível focar via Win32.")
            return False
        return self._ctx.win32.set_focus(info.handle)

    def ensure_foreground(self, info: ElementInfo) -> None:
        """Aplica ``Settings.focus_policy`` antes de uma interação por entrada real.

        ``never``: nada. ``auto``: ativa só se a janela raiz não estiver em
        primeiro plano. ``force``: sempre ativa.
        """
        policy = self._ctx.settings.focus_policy
        if policy == "never" or not info.handle:
            return
        win32 = self._ctx.win32
        root = win32.root_handle(info.handle) or info.handle
        if policy == "force" or win32.foreground_window() != root:
            win32.set_focus(root, control=False)

    def wait_for_change(self, previous: int | None = None, *,
                        timeout: float | None = None) -> ElementInfo:
        """Aguarda o foco mudar de ``previous`` (padrão: do foco atual)."""
        if previous is None:
            cur = self.current()
            previous = cur.handle if cur else 0
        s = self._ctx.settings

        def changed() -> ElementInfo | None:
            now = self.current()
            return now if now is not None and now.handle != previous else None

        return wait_until(changed, timeout=s.timeout if timeout is None else timeout,
                          interval=s.poll_interval, description="mudança de foco")

    def wait_for(self, criteria: Criteria, *, timeout: float | None = None) -> ElementInfo:
        """Aguarda o foco cair em um controle que satisfaça ``criteria``."""
        s = self._ctx.settings

        def matched() -> ElementInfo | None:
            now = self.current()
            return now if now is not None and criteria.matches(now) else None

        return wait_until(matched, timeout=s.timeout if timeout is None else timeout,
                          interval=s.poll_interval, description=f"foco em {criteria.describe()}")

    def trace_tab(self, count: int = 10, *, delay: float = 0.3) -> list[FocusStep]:
        """Pressiona TAB ``count`` vezes e registra o controle focado a cada passo.

        É uma operação de INTERAÇÃO (envia teclas à janela em primeiro plano).
        """
        steps = []
        for i in range(1, count + 1):
            self._ctx.keyboard.press("tab")
            time.sleep(delay)
            steps.append(FocusStep(i, self.current()))
        return steps
