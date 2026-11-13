"""Janelas de nível superior (e qualquer elemento tratado como janela)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..utils.waiting import wait_until
from .element import Element
from .locator import Criteria

if TYPE_CHECKING:
    from ..inspection.hierarchy import TreeNode


class Window(Element):
    """Janela localizada por critérios (título, classe, regex, handle...)."""

    _label = "Janela"

    def is_active(self) -> bool:
        """Verdadeiro se é a janela em primeiro plano."""
        info = self.find()
        fg = self._ctx.backend.foreground()
        return bool(info and fg and fg.handle == info.handle)

    def activate(self) -> bool:
        """Traz a janela ao primeiro plano (INTERAÇÃO; respeita ``focus_policy='never'``)."""
        if self._ctx.settings.focus_policy == "never":
            return False
        return self._ctx.focus.set(self.resolve())

    def wait_for_active(self, timeout: float | None = None) -> "Window":
        wait_until(self.is_active, timeout=self._timeout(timeout),
                   interval=self._ctx.settings.poll_interval, description="janela ativa")
        return self

    def owner(self) -> "Window | None":
        """Janela proprietária (relação *owner*, distinta de pai/filho)."""
        info = self.resolve()
        owner = self._ctx.backend.from_handle(info.owner) if info.owner else None
        return Window(self._ctx, info=owner) if owner else None

    def owned_windows(self, **criteria: Any) -> list["Window"]:
        """Janelas de nível superior pertencentes a esta (diálogos, popups)."""
        me = self.resolve().handle
        crit = Criteria(**criteria)
        return [Window(self._ctx, info=i)
                for i in crit.select(i for i in self._ctx.backend.top_level() if i.owner == me)]

    def tree(self, max_depth: int | None = None) -> "TreeNode":
        """Árvore completa de controles desta janela."""
        from ..inspection.hierarchy import build_control_tree
        return build_control_tree(self._ctx, self.resolve(), max_depth=max_depth)
