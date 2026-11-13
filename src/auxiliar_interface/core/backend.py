"""Backends de descoberta de elementos: o contrato e a implementação Win32.

Um backend sabe enumerar elementos e produzir ``ElementInfo``. Janelas, controles
e diagnósticos dependem apenas deste contrato, o que permite trocar Win32 por
UIA (ou por um backend falso nos testes) sem alterar o restante da biblioteca.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..config import Settings
from ..exceptions import InvalidHandleError
from .models import ElementInfo

if TYPE_CHECKING:
    from ..native.win32 import Win32


@runtime_checkable
class Backend(Protocol):
    """Contrato mínimo de um backend."""

    name: str

    def top_level(self) -> list[ElementInfo]: ...
    def children(self, parent: ElementInfo) -> list[ElementInfo]: ...
    def descendants(self, parent: ElementInfo) -> list[ElementInfo]: ...
    def from_handle(self, handle: int) -> ElementInfo | None: ...
    def refresh(self, info: ElementInfo) -> ElementInfo | None: ...
    def exists(self, info: ElementInfo) -> bool: ...
    def parent_or_owner(self, handle: int) -> int: ...
    def at_point(self, x: int, y: int) -> ElementInfo | None: ...
    def focused(self) -> ElementInfo | None: ...
    def foreground(self) -> ElementInfo | None: ...


class Win32Backend:
    """Backend baseado em ``user32`` (rápido; ideal para aplicativos Delphi/VCL)."""

    name = "win32"

    def __init__(self, api: "Win32", settings: Settings | None = None) -> None:
        self.api = api
        self.settings = settings or Settings()

    # ------------------------------------------------------------- leitura
    def _title(self, hwnd: int, is_child: bool) -> str:
        """Título conforme ``Settings.text_source``.

        ``fast``: só GetWindowText. ``message``: WM_GETTEXT sempre.
        ``auto``: GetWindowText e, se vazio num controle filho, WM_GETTEXT
        (necessário para Edits Delphi/DevExpress; usa timeout curto).
        """
        mode, timeout = self.settings.text_source, self.settings.message_timeout_ms
        if mode == "message":
            text = self.api.get_text_message(hwnd, timeout)
            return text if text is not None else self.api.get_text(hwnd)
        text = self.api.get_text(hwnd)
        if not text and mode == "auto" and is_child:
            text = self.api.get_text_message(hwnd, timeout) or ""
        return text

    def _read(self, hwnd: int) -> ElementInfo | None:
        api = self.api
        if not api.is_window(hwnd):
            return None
        parent = api.parent_handle(hwnd)
        tid, pid = api.thread_and_process(hwnd)
        return ElementInfo(
            handle=hwnd,
            title=self._title(hwnd, is_child=bool(parent)),
            class_name=api.get_class_name(hwnd),
            rect=api.get_rect(hwnd),
            visible=api.is_visible(hwnd),
            enabled=api.is_enabled(hwnd),
            parent=parent,
            owner=api.owner_handle(hwnd),
            process_id=pid,
            thread_id=tid,
        )

    def _read_all(self, handles: list[int]) -> list[ElementInfo]:
        infos = (self._read(h) for h in handles)
        return [i for i in infos if i is not None]  # janelas podem sumir no meio

    # ----------------------------------------------------------- contrato
    def top_level(self) -> list[ElementInfo]:
        return self._read_all(self.api.enum_top_level())

    def children(self, parent: ElementInfo) -> list[ElementInfo]:
        return self._read_all(self.api.children(parent.handle))

    def descendants(self, parent: ElementInfo) -> list[ElementInfo]:
        return self._read_all(self.api.enum_descendants(parent.handle))

    def from_handle(self, handle: int) -> ElementInfo | None:
        return self._read(handle)

    def require(self, handle: int) -> ElementInfo:
        info = self._read(handle)
        if info is None:
            raise InvalidHandleError(f"Handle inválido ou janela inexistente: {handle}")
        return info

    def refresh(self, info: ElementInfo) -> ElementInfo | None:
        return self._read(info.handle) if info.handle else None

    def exists(self, info: ElementInfo) -> bool:
        return self.api.is_window(info.handle)

    def parent_or_owner(self, handle: int) -> int:
        """Pai direto (GA_PARENT); se não houver, a janela proprietária."""
        return self.api.parent_handle(handle) or self.api.owner_handle(handle)

    def at_point(self, x: int, y: int) -> ElementInfo | None:
        hwnd = self.api.window_from_point(x, y)
        return self._read(hwnd) if hwnd else None

    def focused(self) -> ElementInfo | None:
        gui = self.api.gui_thread_info()
        return self._read(gui.focus) if gui and gui.focus else None

    def foreground(self) -> ElementInfo | None:
        hwnd = self.api.foreground_window()
        return self._read(hwnd) if hwnd else None


def make_backend(name: str, win32: "Win32", settings: Settings) -> Backend:
    """Cria o backend pelo nome (``"win32"`` ou ``"uia"``)."""
    if name == "win32":
        return Win32Backend(win32, settings)
    if name == "uia":
        from ..native.uia import UiaBackend
        return UiaBackend(win32, settings)
    raise ValueError(f"Backend desconhecido: {name!r}")
