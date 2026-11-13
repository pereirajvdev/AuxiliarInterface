"""Diagnóstico de grades e componentes complexos (DevExpress ``TcxGrid``/``TcxGridSite``).

Totalmente somente leitura. Combina três visões independentes, porque cada
componente expõe uma coisa diferente:

1. **Win32**: janelas-filhas, rectângulos e mensagens de texto (WM_GETTEXT).
2. **UIA**: elementos, tipos, padrões de acessibilidade.
3. **MSAA**: objetos ``IAccessible`` e seus filhos (nome, valor, estado...).

Nada garante que o componente publique dados em alguma delas; o relatório
mostra o que cada fonte realmente devolveu (inclusive "nada").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from ..core.locator import Criteria
from ..core.window import Window
from ..exceptions import AuxiliarInterfaceError, ElementNotFoundError, backend_errors
from ..native import win32 as w
from ..utils.formatting import Report
from .accessibility import msaa_subtree, uia_subtree

if TYPE_CHECKING:
    from ..core.context import Context

DEFAULT_GRID_CLASSES = ("TcxGrid", "TcxGridSite")


def grid_report(ctx: "Context", window: Criteria, *, tab_title: str | None = None,
                tab_class: str = "TTabSheet", grid_classes: Sequence[str] = DEFAULT_GRID_CLASSES,
                use_win32: bool = True, use_uia: bool = True, use_msaa: bool = True,
                msaa_depth: int = 1, max_children: int = 50,
                uia_limit: int | None = None) -> Report:
    """Investiga as grades de ``window`` (opcionalmente restritas a uma aba)."""
    win = Window(ctx, window).resolve()
    data: dict[str, Any] = {"window": win.to_dict()}
    scope = win
    if tab_title is not None:
        wanted = tab_title.strip()
        tabs = Criteria(class_name=tab_class,
                        predicate=lambda i: i.title.strip() == wanted).select(ctx.backend.descendants(win))
        if not tabs:
            raise ElementNotFoundError(f"{tab_class} com título {tab_title!r} não encontrado.")
        scope = tabs[0]
        data["tab"] = scope.to_dict()
    grids = Criteria(class_name=tuple(grid_classes)).select(ctx.backend.descendants(scope))
    data["grids_found"] = len(grids)
    if not grids:
        data["note"] = ("Nenhuma grade encontrada pelas classes informadas. O componente pode não "
                        "expor janelas-filhas via Win32; tente a seção UIA/MSAA no nível da janela.")

    if use_win32:
        data["win32"] = [_win32_view(ctx, g.handle) for g in grids if g.handle]
    if use_uia:
        try:
            data["uia"] = uia_subtree(ctx, scope, limit=uia_limit)
        except (AuxiliarInterfaceError, *backend_errors()) as exc:
            data["uia"] = {"erro": f"{type(exc).__name__}: {exc}"}
    if use_msaa:
        data["msaa"] = [
            {"handle": g.handle, "class_name": g.class_name,
             "tree": msaa_subtree(ctx, g.handle, depth=msaa_depth, max_children=max_children)}
            for g in grids if g.handle
        ]
    return Report("Diagnóstico de grade", data)


def _win32_view(ctx: "Context", hwnd: int) -> dict[str, Any]:
    """Consulta de texto por mensagens (WM_GETTEXTLENGTH/WM_GETTEXT): não altera nada."""
    api, timeout = ctx.win32, ctx.settings.message_timeout_ms
    return {
        "handle": hwnd,
        "class_name": api.get_class_name(hwnd),
        "window_text": api.get_text(hwnd),
        "rect": api.get_rect(hwnd).to_tuple(),
        "parent": api.parent_handle(hwnd),
        "WM_GETTEXTLENGTH": api.send_message(hwnd, w.WM_GETTEXTLENGTH, 0, 0, timeout),
        "WM_GETTEXT": api.get_text_message(hwnd, timeout),
    }
