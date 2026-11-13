"""Dados de acessibilidade (UIA e MSAA) em forma de dicionários para relatórios."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.models import ElementInfo
from ..exceptions import AuxiliarInterfaceError, backend_errors
from ..native.uia import uia_properties, wrapper_for_handle

if TYPE_CHECKING:
    from ..core.context import Context


def uia_subtree(ctx: "Context", root: ElementInfo, *, include_root: bool = True,
                limit: int | None = None) -> list[dict[str, Any]]:
    """Propriedades UIA de ``root`` e de seus descendentes (somente leitura)."""
    wrapper = root.native if root.native is not None else wrapper_for_handle(root.handle, "uia")
    items = ([wrapper] if include_root else []) + list(wrapper.descendants())
    if limit is not None:
        items = items[:limit]
    out = []
    for item in items:
        try:
            out.append(uia_properties(item))
        except backend_errors() as exc:
            out.append({"erro": f"{type(exc).__name__}: {exc}"})
    return out


def msaa_subtree(ctx: "Context", handle: int, *, depth: int = 1, max_children: int = 50) -> dict[str, Any]:
    """Árvore MSAA de um HWND; erros viram ``{"erro": ...}``."""
    try:
        return ctx.msaa.inspect_window(handle, depth=depth, max_children=max_children).to_dict()
    except (AuxiliarInterfaceError, *backend_errors()) as exc:
        return {"erro": f"{type(exc).__name__}: {exc}"}


def msaa_at_point(ctx: "Context", x: int, y: int) -> dict[str, Any]:
    """Objeto MSAA sob uma coordenada (alcança elementos sem HWND)."""
    try:
        acc, child_id = ctx.msaa.from_point(x, y)
        return ctx.msaa.describe(acc, child_id).to_dict()
    except (AuxiliarInterfaceError, *backend_errors()) as exc:
        return {"erro": f"{type(exc).__name__}: {exc}"}


def accessibility_summary(ctx: "Context", info: ElementInfo) -> dict[str, Any]:
    """Resumo UIA + MSAA de um elemento, cada fonte isolada de falhas."""
    out: dict[str, Any] = {}
    try:
        wrapper = info.native if info.native is not None else wrapper_for_handle(info.handle, "uia")
        out["uia"] = uia_properties(wrapper)
    except (AuxiliarInterfaceError, *backend_errors()) as exc:
        out["uia"] = {"erro": f"{type(exc).__name__}: {exc}"}
    out["msaa"] = msaa_subtree(ctx, info.handle, depth=0) if info.handle else {"erro": "sem HWND"}
    return out

