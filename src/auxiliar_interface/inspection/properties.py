"""Investigação de propriedades textuais (Name, Text, Caption, Hint, Description, Help...).

``window_text()`` sozinho não basta em controles Delphi/DevExpress; aqui as
fontes são combinadas e cada uma é rotulada, para saber de onde veio o dado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from ..automation.actions import control_kind
from ..core.models import ElementInfo
from ..exceptions import AuxiliarInterfaceError, backend_errors
from ..native.uia import uia_properties, wrapper_for_handle

if TYPE_CHECKING:
    from ..core.context import Context

TEXT_KEYWORDS = ("text", "name", "title", "caption", "description", "help", "hint")
SOURCES = ("native", "pywinauto", "uia", "msaa")


def native_properties(ctx: "Context", info: ElementInfo) -> dict[str, Any]:
    """Propriedades lidas diretamente da API Win32 (somente leitura)."""
    if not info.handle:
        return {}
    win32 = ctx.win32
    style, ex_style = win32.get_styles(info.handle)
    kind = control_kind(info.class_name)
    props: dict[str, Any] = {
        "window_text (GetWindowText)": win32.get_text(info.handle),
        "window_text (WM_GETTEXT)": win32.get_text_message(info.handle, ctx.settings.message_timeout_ms),
        "kind": kind,
        "control_id": win32.control_id(info.handle),
        "style": f"0x{style:08X}",
        "ex_style": f"0x{ex_style:08X}",
        "thread_id": info.thread_id,
        "process_id": info.process_id,
    }
    if kind in ("combo", "list"):
        props["items"] = ctx.ops.items(info.handle, kind)
    if kind == "button":
        try:
            props["check_state"] = ctx.ops.check_state(info.handle)
        except AuxiliarInterfaceError as exc:
            props["check_state"] = f"<indisponível: {exc}>"
    return props


def pywinauto_properties(info: ElementInfo, backend: str) -> dict[str, Any]:
    """``get_properties()`` do wrapper pywinauto (win32 ou uia)."""
    wrapper = info.native if info.native is not None else wrapper_for_handle(info.handle, backend)
    return dict(wrapper.get_properties())


def collect_properties(ctx: "Context", info: ElementInfo,
                       sources: Iterable[str] = ("native", "pywinauto")) -> dict[str, dict[str, Any]]:
    """Reúne propriedades por fonte. Falhas viram ``{"erro": ...}`` na própria fonte."""
    out: dict[str, dict[str, Any]] = {}
    for source in sources:
        try:
            if source == "native":
                out[source] = native_properties(ctx, info)
            elif source == "pywinauto":
                out[source] = pywinauto_properties(info, ctx.settings.backend)
            elif source == "uia":
                wrapper = info.native if info.native is not None else wrapper_for_handle(info.handle, "uia")
                out[source] = uia_properties(wrapper)
            elif source == "msaa":
                node = ctx.msaa.inspect_window(info.handle, depth=0)
                out[source] = node.to_dict()
            else:
                raise ValueError(f"Fonte desconhecida: {source!r} (use {SOURCES})")
        except (AuxiliarInterfaceError, *backend_errors()) as exc:
            out[source] = {"erro": f"{type(exc).__name__}: {exc}"}
    return out


def textual_properties(props: dict[str, Any], keywords: Iterable[str] = TEXT_KEYWORDS) -> dict[str, Any]:
    """Filtra propriedades cujo nome contém uma palavra-chave e cujo valor não é vazio."""
    keys = tuple(k.lower() for k in keywords)
    found = {}
    for name, value in props.items():
        if value is None or not str(value).strip():
            continue
        if any(k in name.lower() for k in keys):
            found[name] = value
    return found
