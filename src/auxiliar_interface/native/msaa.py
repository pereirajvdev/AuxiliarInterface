"""MSAA (IAccessible) via comtypes/oleacc — somente leitura.

Útil para componentes que não expõem filhos por Win32 (ex.: DevExpress
``TcxGrid``/``TcxGridSite``). Nada aqui clica, digita ou altera dados.

As referências COM são gerenciadas pelo comtypes (liberadas quando o objeto
Python é coletado); por isso não há chamadas manuais a ``Release()``.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import (BackendUnavailableError, MsaaError,
                          PlatformNotSupportedError, backend_errors)
from ..utils.logging import get_logger

log = get_logger("msaa")

OBJID_WINDOW = 0x00000000
OBJID_CLIENT = 0xFFFFFFFC
CHILDID_SELF = 0
VT_I4, VT_DISPATCH, VT_UNKNOWN = 3, 9, 13

_PROPERTIES = ("accName", "accValue", "accDescription", "accRole", "accState",
               "accDefaultAction", "accHelp", "accKeyboardShortcut")


@dataclass
class MsaaNode:
    """Um objeto (ou filho simples) da árvore MSAA."""

    child_id: int = CHILDID_SELF
    kind: str = "object"            # object | simple
    name: str | None = None
    value: str | None = None
    description: str | None = None
    role: int | None = None
    role_text: str | None = None
    state: int | None = None
    state_texts: list[str] = field(default_factory=list)
    default_action: str | None = None
    help: str | None = None
    keyboard_shortcut: str | None = None
    child_count: int | None = None
    children: list["MsaaNode"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "child_id": self.child_id, "kind": self.kind, "name": self.name,
            "value": self.value, "description": self.description,
            "role": self.role_text or self.role, "state": self.state_texts or self.state,
            "default_action": self.default_action, "help": self.help,
            "child_count": self.child_count,
        }
        if self.errors:
            data["errors"] = self.errors
        if self.children:
            data["children"] = [c.to_dict() for c in self.children]
        return data


class MsaaClient:
    """Cliente MSAA. Cria-se uma vez e reutiliza-se (carrega o typelib uma vez)."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise PlatformNotSupportedError("MSAA só está disponível no Windows.")
        try:
            import comtypes.client
            from comtypes.automation import VARIANT
        except ImportError as exc:
            raise BackendUnavailableError("comtypes não está instalado (pip install comtypes).") from exc
        comtypes.client.GetModule("oleacc.dll")
        from comtypes.gen.Accessibility import IAccessible  # type: ignore[import-not-found]

        self._IAccessible = IAccessible
        self._VARIANT = VARIANT
        self._oleacc = ctypes.OleDLL("oleacc")  # HRESULTs de erro viram OSError
        self._oleacc.AccessibleObjectFromWindow.argtypes = [
            wintypes.HWND, wintypes.DWORD, ctypes.POINTER(comtypes.GUID), ctypes.c_void_p]
        self._oleacc.AccessibleChildren.argtypes = [
            ctypes.c_void_p, ctypes.c_long, ctypes.c_long,
            ctypes.POINTER(VARIANT), ctypes.POINTER(ctypes.c_long)]
        self._oleacc.AccessibleObjectFromPoint.argtypes = [
            wintypes.POINT, ctypes.c_void_p, ctypes.POINTER(VARIANT)]
        self._oleacc.GetRoleTextW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.UINT]
        self._oleacc.GetStateTextW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.UINT]
        self._oleacc.GetRoleTextW.restype = wintypes.UINT
        self._oleacc.GetStateTextW.restype = wintypes.UINT
        self._comerrors = backend_errors()

    # ------------------------------------------------------------- acesso
    def from_window(self, hwnd: int, object_id: int = OBJID_CLIENT) -> Any:
        """IAccessible do HWND. ``MsaaError`` se o controle não implementar MSAA."""
        ptr = ctypes.POINTER(self._IAccessible)()
        try:
            self._oleacc.AccessibleObjectFromWindow(
                hwnd, object_id, ctypes.byref(self._IAccessible._iid_), ctypes.byref(ptr))
        except OSError as exc:
            raise MsaaError(f"AccessibleObjectFromWindow falhou para {hwnd}: {exc}") from exc
        if not ptr:
            raise MsaaError(f"Sem interface IAccessible para o handle {hwnd}.")
        return ptr

    def from_point(self, x: int, y: int) -> tuple[Any, int]:
        """(IAccessible, child_id) sob a coordenada de tela; alcança elementos sem HWND."""
        ptr = ctypes.POINTER(self._IAccessible)()
        child = self._VARIANT()
        try:
            self._oleacc.AccessibleObjectFromPoint(
                wintypes.POINT(int(x), int(y)), ctypes.byref(ptr), ctypes.byref(child))
        except OSError as exc:
            raise MsaaError(f"AccessibleObjectFromPoint falhou em ({x}, {y}): {exc}") from exc
        if not ptr:
            raise MsaaError(f"Nenhum objeto acessível em ({x}, {y}).")
        child_id = int(child.value) if child.vt == VT_I4 else CHILDID_SELF
        return ptr, child_id

    # ------------------------------------------------------------ leitura
    def _text(self, fn: Any, value: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        return buf.value if fn(value, buf, 256) else ""

    def role_text(self, role: int) -> str:
        return self._text(self._oleacc.GetRoleTextW, role)

    def state_texts(self, state: int) -> list[str]:
        out = []
        for bit in range(32):
            flag = 1 << bit
            if state & flag:
                text = self._text(self._oleacc.GetStateTextW, flag)
                out.append(text or f"0x{flag:X}")
        return out

    def _prop(self, acc: Any, name: str, child_id: int, node: MsaaNode) -> Any:
        try:
            attr = getattr(acc, name)
            if isinstance(attr, (str, int, float, bool)):
                return attr
            try:
                return attr(child_id)
            except TypeError:
                return attr[child_id]
        except self._comerrors as exc:
            node.errors.append(f"{name}: {exc}")
            return None

    def describe(self, acc: Any, child_id: int = CHILDID_SELF) -> MsaaNode:
        """Lê as propriedades MSAA de um objeto (ou de um filho simples)."""
        node = MsaaNode(child_id=child_id, kind="object" if child_id == CHILDID_SELF else "simple")
        raw = {p: self._prop(acc, p, child_id, node) for p in _PROPERTIES}
        node.name = _as_text(raw["accName"])
        node.value = _as_text(raw["accValue"])
        node.description = _as_text(raw["accDescription"])
        node.default_action = _as_text(raw["accDefaultAction"])
        node.help = _as_text(raw["accHelp"])
        node.keyboard_shortcut = _as_text(raw["accKeyboardShortcut"])
        if isinstance(raw["accRole"], int):
            node.role = raw["accRole"]
            node.role_text = self.role_text(node.role)
        if isinstance(raw["accState"], int):
            node.state = raw["accState"]
            node.state_texts = self.state_texts(node.state)
        if child_id == CHILDID_SELF:
            try:
                node.child_count = int(acc.accChildCount)
            except self._comerrors as exc:
                node.errors.append(f"accChildCount: {exc}")
        return node

    def inspect(self, acc: Any, *, depth: int = 1, max_children: int = 50) -> MsaaNode:
        """Árvore MSAA a partir de ``acc`` com profundidade e nº de filhos limitados."""
        node = self.describe(acc)
        count = node.child_count or 0
        if depth <= 0 or count <= 0:
            return node
        wanted = min(count, max_children)
        variants = (self._VARIANT * wanted)()
        got = ctypes.c_long(0)
        try:
            self._oleacc.AccessibleChildren(acc, 0, wanted, variants, ctypes.byref(got))
        except OSError as exc:
            node.errors.append(f"AccessibleChildren: {exc}")
            return node
        for i in range(got.value):
            v = variants[i]
            if v.vt == VT_I4:
                node.children.append(self.describe(acc, int(v.value)))
            elif v.vt in (VT_DISPATCH, VT_UNKNOWN):
                try:
                    child = v.value.QueryInterface(self._IAccessible)
                    node.children.append(self.inspect(child, depth=depth - 1, max_children=max_children))
                except self._comerrors as exc:
                    node.errors.append(f"filho {i}: {exc}")
            else:
                node.errors.append(f"filho {i}: VARIANT.vt={v.vt} não tratado")
        if count > wanted:
            node.errors.append(f"{count - wanted} filhos omitidos (max_children={max_children})")
        return node

    def inspect_window(self, hwnd: int, *, depth: int = 1, max_children: int = 50) -> MsaaNode:
        return self.inspect(self.from_window(hwnd), depth=depth, max_children=max_children)


def _as_text(value: Any) -> str | None:
    return None if value is None else str(value)
