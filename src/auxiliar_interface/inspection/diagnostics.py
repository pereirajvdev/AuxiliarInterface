"""Relatórios de diagnóstico (somente leitura) reutilizando uma coleta única de dados."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Iterator, Sequence

from ..core.locator import Criteria
from ..core.models import ElementInfo
from ..core.window import Window
from ..exceptions import (AuxiliarInterfaceError, ElementNotFoundError,
                          PlatformNotSupportedError, backend_errors)
from ..utils.formatting import Report, Text
from .accessibility import (accessibility_summary, msaa_at_point, msaa_subtree,
                            uia_subtree)
from .grid import DEFAULT_GRID_CLASSES, grid_report
from .hierarchy import build_control_tree, build_window_tree
from .properties import collect_properties

if TYPE_CHECKING:
    from ..core.context import Context


def ancestors_of(ctx: "Context", info: ElementInfo, limit: int = 10) -> list[ElementInfo]:
    """Pais do mais próximo ao mais distante (até ``limit``)."""
    out: list[ElementInfo] = []
    cur = info
    while cur.parent and len(out) < limit:
        parent = ctx.backend.from_handle(cur.parent)
        if parent is None:
            break
        out.append(parent)
        cur = parent
    return out


def element_details(ctx: "Context", info: ElementInfo, *, sources: Sequence[str] = ("native",),
                    accessibility: bool = False, ancestors: bool = False) -> dict[str, Any]:
    """Dicionário completo de um elemento; reutilizado por todos os relatórios."""
    data = info.to_dict()
    if sources:
        data["properties"] = collect_properties(ctx, info, sources)
    if accessibility:
        data["accessibility"] = accessibility_summary(ctx, info)
    if ancestors:
        data["ancestors"] = [a.to_dict() for a in ancestors_of(ctx, info)]
    return data


def window_report(ctx: "Context", criteria: Criteria, *, descendants: bool = True,
                  accessibility: bool = False) -> Report:
    """Título, classe, handle, estados, geometria, filhos, descendentes e textos."""
    info = Window(ctx, criteria).resolve()
    backend = ctx.backend
    foreground = backend.foreground()
    direct = backend.children(info)
    everything = backend.descendants(info) if descendants else []
    data: dict[str, Any] = {
        "window": info.to_dict(),
        "active": bool(foreground and foreground.handle == info.handle),
        "owned_windows": [i.to_dict() for i in backend.top_level() if info.handle and i.owner == info.handle],
        "direct_children_count": len(direct),
        "direct_children": [c.to_dict() for c in direct],
    }
    if descendants:
        data["descendants_count"] = len(everything)
        data["texts"] = [{"handle": c.handle, "class_name": c.class_name, "text": c.title}
                         for c in everything if c.has_text]
        data["descendants"] = [c.to_dict() for c in everything]
    if accessibility:
        data["accessibility"] = accessibility_summary(ctx, info)
    return Report("Diagnóstico da janela", data)


def controls_report(ctx: "Context", window: Criteria | None, controls: Criteria, *,
                    direct: bool = False, sources: Sequence[str] = ("native",),
                    accessibility: bool = False, textual_only: bool = False) -> Report:
    """Detalha todos os controles que satisfazem ``controls`` (dentro de ``window``)."""
    from .properties import textual_properties

    if window is not None:
        root = Window(ctx, window).resolve()
        pool = ctx.backend.children(root) if direct else ctx.backend.descendants(root)
        found = controls.select(pool)
    elif controls.handle is not None:
        info = ctx.backend.from_handle(controls.handle)
        found = [info] if info is not None and controls.matches(info) else []
    else:
        raise ValueError("Informe a janela (title/class/handle da janela) ou o handle do controle.")
    items = []
    for info in found:
        item = element_details(ctx, info, sources=sources, accessibility=accessibility, ancestors=True)
        if textual_only:
            textual = {src: textual_properties(props) for src, props in item.get("properties", {}).items()
                       if isinstance(props, dict)}
            item["textual"] = {k: v for k, v in textual.items() if v}
        items.append(item)
    return Report("Diagnóstico de controles", {"total": len(items), "controls": items})


def focus_report(ctx: "Context") -> Report:
    """Quem tem o foco agora (somente leitura)."""
    data: dict[str, Any] = {}
    foreground = ctx.focus.foreground_window()
    data["foreground_window"] = foreground.to_dict() if foreground else None
    try:
        gui = ctx.win32.gui_thread_info()
        data["gui_thread"] = vars(gui) if gui else None
    except PlatformNotSupportedError:
        pass
    focused = ctx.focus.current()
    if focused is None:
        data["focused_control"] = None
    else:
        data["focused_control"] = element_details(ctx, focused, sources=(), ancestors=True)
    return Report("Diagnóstico de foco", data)


def mouse_report(ctx: "Context", *, accessibility: bool = False) -> Report:
    """Controle sob o cursor, seus pais e filhos (não clica)."""
    x, y = ctx.mouse.position
    data: dict[str, Any] = {"position": {"x": x, "y": y}}
    info = ctx.backend.at_point(x, y)
    if info is None:
        data["control"] = None
        return Report("Diagnóstico do mouse", data)
    data["control"] = info.to_dict()
    data["ancestors"] = [a.to_dict() for a in ancestors_of(ctx, info)]
    data["children"] = [c.to_dict() for c in ctx.backend.children(info)]
    if accessibility:
        data["msaa_at_point"] = msaa_at_point(ctx, x, y)
    return Report("Diagnóstico do mouse", data)


def monitor_mouse(ctx: "Context", *, interval: float = 0.05,
                  max_samples: int | None = None) -> Iterator[dict[str, Any]]:
    """Gera uma amostra a cada mudança de posição do cursor (interrompa com Ctrl+C)."""
    last: tuple[int, int] | None = None
    produced = 0
    while max_samples is None or produced < max_samples:
        pos = ctx.mouse.position
        if pos != last:
            last = pos
            info = ctx.backend.at_point(*pos)
            yield {"x": pos[0], "y": pos[1], "handle": info.handle if info else 0,
                   "class_name": info.class_name if info else ""}
            produced += 1
        time.sleep(interval)


def hierarchy_report(ctx: "Context", criteria: Criteria | None, *, windows: bool = False,
                     max_depth: int | None = None, hide_noise: bool = True,
                     include_untitled: bool = False) -> Report:
    """Árvore de janelas (``windows=True``) ou de controles de uma janela."""
    if windows:
        roots = build_window_tree(ctx, criteria, hide_noise=hide_noise,
                                  include_untitled=include_untitled)
        text = "\n\n".join(r.render() for r in roots)
        return Report("Hierarquia de janelas", {"roots": len(roots),
                                                "windows": sum(r.count() for r in roots),
                                                "tree": Text(text)})
    info = Window(ctx, criteria or Criteria()).resolve()
    tree = build_control_tree(ctx, info, max_depth=max_depth)
    return Report("Hierarquia de controles", {"controls": tree.count() - 1, "tree": Text(tree.render())})


class Diagnostics:
    """Fachada dos diagnósticos (acessível por ``DesktopAutomation.diagnostics``)."""

    def __init__(self, ctx: "Context") -> None:
        self._ctx = ctx

    def window(self, criteria: Criteria, **kw: Any) -> Report:
        return window_report(self._ctx, criteria, **kw)

    def controls(self, window: Criteria | None, controls: Criteria, **kw: Any) -> Report:
        return controls_report(self._ctx, window, controls, **kw)

    def focus(self) -> Report:
        return focus_report(self._ctx)

    def mouse(self, **kw: Any) -> Report:
        return mouse_report(self._ctx, **kw)

    def hierarchy(self, criteria: Criteria | None = None, **kw: Any) -> Report:
        return hierarchy_report(self._ctx, criteria, **kw)

    def uia(self, window: Criteria, controls: Criteria | None = None, *,
            limit: int | None = None) -> Report:
        """Propriedades e padrões UIA da janela (ou dos controles indicados)."""
        root = Window(self._ctx, window).resolve()
        targets = [root]
        if controls is not None:
            targets = controls.select(self._ctx.backend.descendants(root))
            if not targets:
                raise ElementNotFoundError(f"Nenhum controle satisfaz: {controls.describe()}")
        data = {"targets": [
            {"element": t.to_dict(), "uia": _guard(lambda t=t: uia_subtree(self._ctx, t, limit=limit))}
            for t in targets]}
        return Report("Diagnóstico UIA", data)

    def msaa(self, window: Criteria, controls: Criteria | None = None, *,
             depth: int = 1, max_children: int = 50) -> Report:
        """Árvore MSAA do HWND da janela (ou dos controles indicados)."""
        root = Window(self._ctx, window).resolve()
        targets = [root]
        if controls is not None:
            targets = controls.select(self._ctx.backend.descendants(root))
            if not targets:
                raise ElementNotFoundError(f"Nenhum controle satisfaz: {controls.describe()}")
        data = {"targets": [
            {"element": t.to_dict(), "msaa": msaa_subtree(self._ctx, t.handle, depth=depth,
                                                          max_children=max_children)}
            for t in targets if t.handle]}
        return Report("Diagnóstico MSAA", data)

    def grid(self, window: Criteria, **kw: Any) -> Report:
        kw.setdefault("grid_classes", DEFAULT_GRID_CLASSES)
        return grid_report(self._ctx, window, **kw)


def _guard(fn: Any) -> Any:
    """Executa ``fn``; erros esperados de UIA/COM viram um item ``{"erro": ...}``."""
    try:
        return fn()
    except (AuxiliarInterfaceError, *backend_errors()) as exc:
        return {"erro": f"{type(exc).__name__}: {exc}"}
