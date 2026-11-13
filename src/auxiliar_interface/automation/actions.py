"""Leitura/escrita de valores de controles padrão por mensagens Win32.

Funciona com controles nativos e com os equivalentes Delphi (``TEdit``,
``TComboBox``, ``TListBox``, ``TCheckBox``...), que são subclasses dos
controles do Windows. Para componentes desenhados à mão (DevExpress, grades),
prefira UIA/MSAA: aqui não há promessa de que a mensagem seja entendida.
"""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from ..config import Settings
from ..exceptions import ElementNotFoundError, ElementStateError
from ..native import win32 as w

if TYPE_CHECKING:
    from ..native.win32 import Win32

CHECK_STATES = {0: "unchecked", 1: "checked", 2: "indeterminate"}


def control_kind(class_name: str) -> str:
    """Classifica pela classe: ``combo``, ``list``, ``button``, ``edit`` ou ``unknown``."""
    name = class_name.lower()
    if "combo" in name:
        return "combo"
    if "listbox" in name:
        return "list"
    if name.endswith("button") or any(k in name for k in ("checkbox", "radiobutton", "bitbtn")):
        return "button"
    if "edit" in name or "memo" in name:
        return "edit"
    return "unknown"


class ControlOps:
    """Operações de valor sobre um HWND."""

    def __init__(self, win32: "Win32", settings: Settings) -> None:
        self._w = win32
        self._t = settings.message_timeout_ms

    # --------------------------------------------------------------- texto
    def get_text(self, hwnd: int) -> str:
        text = self._w.get_text_message(hwnd, self._t)
        return text if text is not None else self._w.get_text(hwnd)

    def set_text(self, hwnd: int, text: str) -> None:
        """Define o texto por WM_SETTEXT (não simula digitação)."""
        buf = ctypes.create_unicode_buffer(text)
        if self._w.send_message(hwnd, w.WM_SETTEXT, 0, ctypes.addressof(buf), self._t) is None:
            raise ElementStateError(f"O controle {hwnd} não respondeu a WM_SETTEXT.")

    # --------------------------------------------------------------- listas
    def _list_messages(self, kind: str) -> tuple[int, int, int, int]:
        if kind == "combo":
            return w.CB_GETCOUNT, w.CB_GETLBTEXTLEN, w.CB_GETLBTEXT, w.CB_GETCURSEL
        if kind == "list":
            return w.LB_GETCOUNT, w.LB_GETTEXTLEN, w.LB_GETTEXT, w.LB_GETCURSEL
        raise ElementStateError(f"Controle do tipo {kind!r} não possui lista de itens.")

    def items(self, hwnd: int, kind: str) -> list[str]:
        """Itens de um ComboBox/ListBox."""
        count_msg, len_msg, text_msg, _ = self._list_messages(kind)
        count = self._w.send_message(hwnd, count_msg, 0, 0, self._t) or 0
        items = []
        for i in range(max(count, 0)):
            length = self._w.send_message(hwnd, len_msg, i, 0, self._t)
            if length is None or length < 0:
                continue
            buf = ctypes.create_unicode_buffer(length + 2)
            if self._w.send_message(hwnd, text_msg, i, ctypes.addressof(buf), self._t) is not None:
                items.append(buf.value)
        return items

    def selected_index(self, hwnd: int, kind: str) -> int:
        """Índice selecionado (-1 se nenhum)."""
        sel = self._w.send_message(hwnd, self._list_messages(kind)[3], 0, 0, self._t)
        return -1 if sel is None else sel

    def select(self, hwnd: int, kind: str, item: str | int, *, notify: bool = True) -> int:
        """Seleciona por índice ou texto exato. Devolve o índice selecionado."""
        items = self.items(hwnd, kind)
        if isinstance(item, int):
            index = item
        else:
            try:
                index = items.index(item)
            except ValueError:
                raise ElementNotFoundError(f"Item {item!r} não encontrado em {items!r}") from None
        if not 0 <= index < len(items):
            raise ElementNotFoundError(f"Índice {index} fora do intervalo (0..{len(items) - 1}).")
        set_msg = w.CB_SETCURSEL if kind == "combo" else w.LB_SETCURSEL
        self._w.send_message(hwnd, set_msg, index, 0, self._t)
        if notify:  # faz o aplicativo (ex.: OnChange do Delphi) perceber a mudança
            self._w.notify_parent(hwnd, w.SELCHANGE)
        return index

    # --------------------------------------------------------------- botões
    def check_state(self, hwnd: int) -> str:
        """``unchecked`` | ``checked`` | ``indeterminate`` (BM_GETCHECK)."""
        state = self._w.send_message(hwnd, w.BM_GETCHECK, 0, 0, self._t)
        if state is None:
            raise ElementStateError(f"O controle {hwnd} não respondeu a BM_GETCHECK.")
        return CHECK_STATES.get(state, f"unknown({state})")

    # --------------------------------------------------------------- cliques
    def post_click(self, hwnd: int, x: int, y: int, *, button: str = "left",
                   double: bool = False, kind: str = "unknown") -> None:
        """Clique por mensagem (sem mover o mouse nem exigir janela ativa).

        Botões nativos/Delphi simples recebem BM_CLICK; os demais recebem
        WM_xBUTTONDOWN/UP com coordenadas de cliente calculadas de ``(x, y)``
        (coordenadas de tela). Funciona só em controles que tratam essas mensagens.
        """
        if kind == "button" and button == "left" and not double:
            self._w.post_message(hwnd, w.BM_CLICK)
            return
        down, up = ((w.WM_LBUTTONDOWN, w.WM_LBUTTONUP) if button == "left"
                    else (w.WM_RBUTTONDOWN, w.WM_RBUTTONUP))
        cx, cy = self._w.screen_to_client(hwnd, x, y)
        lparam = ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)
        for _ in range(2 if double else 1):
            self._w.post_message(hwnd, down, 1 if button == "left" else 2, lparam)
            self._w.post_message(hwnd, up, 0, lparam)
