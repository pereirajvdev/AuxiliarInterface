"""Investigação de Hints (tooltips): move o mouse e observa janelas temporárias.

ATENÇÃO: este módulo move o cursor do mouse (é inerente a provocar Hints).
O cursor original é restaurado ao final, salvo ``restore_cursor=False``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable

from ..core.models import ElementInfo

if TYPE_CHECKING:
    from ..core.context import Context

DEFAULT_IGNORED_CLASSES = frozenset({"IME", "TDataSetValidDialog"})


@dataclass(frozen=True)
class HintResult:
    """Hint encontrado e o controle ao qual ele corresponde."""

    control: ElementInfo          # controle que estava sendo sondado
    under_cursor: int             # HWND realmente sob o cursor (pode ser filho)
    hint_title: str
    hint_class: str
    hint_handle: int

    def to_dict(self) -> dict:
        return {
            "control_handle": self.control.handle, "control_class": self.control.class_name,
            "control_text": self.control.title, "under_cursor": self.under_cursor,
            "hint": self.hint_title, "hint_class": self.hint_class, "hint_handle": self.hint_handle,
        }


def _snapshot(ctx: "Context") -> dict[int, tuple[str, str]]:
    """handle -> (título, classe) das janelas de nível superior visíveis."""
    w = ctx.win32
    return {h: (w.get_text(h), w.get_class_name(h))
            for h in w.enum_top_level() if w.is_visible(h)}


def probe_point(ctx: "Context", control: ElementInfo, x: int, y: int, *, delay: float | None = None,
                ignored_classes: Iterable[str] = DEFAULT_IGNORED_CLASSES,
                restore_cursor: bool = True) -> list[HintResult]:
    """Move o mouse para ``(x, y)``, espera ``delay`` e devolve Hints surgidos.

    Considera Hint toda janela visível, com texto, que é nova **ou cujo texto
    mudou** desde antes do movimento (Delphi reutiliza a mesma janela de Hint).
    """
    ignored = frozenset(ignored_classes)
    delay = ctx.settings.hint_delay if delay is None else delay
    origin = ctx.mouse.position
    before = _snapshot(ctx)
    try:
        ctx.mouse.move(x, y)
        time.sleep(delay)
        under = ctx.mouse.handle_at(x, y)
        after = _snapshot(ctx)
    finally:
        if restore_cursor:
            ctx.mouse.move(*origin)
    return [
        HintResult(control, under, title, cls, handle)
        for handle, (title, cls) in after.items()
        if title and cls not in ignored and before.get(handle, (None, None))[0] != title
    ]


def probe_hints(ctx: "Context", controls: Iterable[ElementInfo], *, delay: float | None = None,
                ignored_classes: Iterable[str] = DEFAULT_IGNORED_CLASSES,
                include_hidden: bool = False,
                on_progress: Callable[[int, ElementInfo], None] | None = None) -> list[HintResult]:
    """Sonda o centro de cada controle e coleta os Hints exibidos.

    Controles invisíveis ou sem área são ignorados (a menos que ``include_hidden``).
    """
    results: list[HintResult] = []
    origin = ctx.mouse.position
    try:
        for i, control in enumerate(controls):
            if control.rect.is_empty or (not include_hidden and not control.visible):
                continue
            if on_progress:
                on_progress(i, control)
            x, y = control.rect.center
            results += probe_point(ctx, control, x, y, delay=delay,
                                   ignored_classes=ignored_classes, restore_cursor=False)
    finally:
        ctx.mouse.move(*origin)
    return results
