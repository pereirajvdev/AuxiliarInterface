"""API Win32 via ctypes, com todas as assinaturas declaradas em um único lugar.

Todos os ``HWND`` são manipulados como ``int`` Python. As assinaturas usam
``wintypes.HWND``/``WPARAM``/``LPARAM``, que têm o tamanho correto tanto em
Windows de 32 quanto de 64 bits (sem truncar handles ou ponteiros).

O módulo pode ser importado em qualquer sistema; ``Win32()`` só funciona no
Windows (``PlatformNotSupportedError`` nos demais).
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass

from ..core.models import Rect
from ..exceptions import PlatformNotSupportedError

# --- Mensagens e constantes -------------------------------------------------
WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_COMMAND = 0x000C, 0x000D, 0x000E, 0x0111
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0204, 0x0205
BM_GETCHECK, BM_SETCHECK, BM_CLICK = 0x00F0, 0x00F1, 0x00F5
CB_GETCOUNT, CB_GETCURSEL, CB_GETLBTEXT, CB_GETLBTEXTLEN = 0x0146, 0x0147, 0x0148, 0x0149
CB_SETCURSEL, CB_FINDSTRINGEXACT = 0x014E, 0x0158
LB_SETCURSEL, LB_GETCURSEL, LB_GETTEXT, LB_GETTEXTLEN = 0x0186, 0x0188, 0x0189, 0x018A
LB_GETCOUNT, LB_FINDSTRINGEXACT = 0x018B, 0x01A2
EM_SETSEL = 0x00B1
SELCHANGE = 1  # CBN_SELCHANGE == LBN_SELCHANGE

GW_HWNDNEXT, GW_OWNER, GW_CHILD = 2, 4, 5
GA_PARENT, GA_ROOT = 1, 2
GWL_STYLE, GWL_EXSTYLE = -16, -20
SW_RESTORE = 9
SMTO_ABORTIFHUNG = 0x0002

MOUSEEVENTF = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}

_MAX_CHILDREN = 100_000


class _GUITHREADINFO(ctypes.Structure):
    # A estrutura completa (inclusive rcCaret) é obrigatória: o Windows valida
    # cbSize e rejeita a chamada se o tamanho não bater.
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


@dataclass(frozen=True)
class GuiThreadInfo:
    """Estado de GUI da thread em primeiro plano (foco, ativo, captura...)."""

    active: int
    focus: int
    capture: int
    menu_owner: int
    move_size: int
    caret: int


class Win32:
    """Fachada fina sobre ``user32``/``kernel32`` com tipos corretos."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise PlatformNotSupportedError("A API Win32 só está disponível no Windows.")
        self._u = ctypes.WinDLL("user32", use_last_error=True)
        self._k = ctypes.WinDLL("kernel32", use_last_error=True)
        self._enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self._declare()
        self.desktop_hwnd = int(self._u.GetDesktopWindow() or 0)

    # ------------------------------------------------------------ assinaturas
    def _declare(self) -> None:
        u, H, B, U = self._u, wintypes.HWND, wintypes.BOOL, wintypes.UINT
        sig = {
            "EnumWindows": ([self._enum_proc, wintypes.LPARAM], B),
            "EnumChildWindows": ([H, self._enum_proc, wintypes.LPARAM], B),
            "GetWindow": ([H, U], H),
            "GetAncestor": ([H, U], H),
            "GetParent": ([H], H),
            "GetDesktopWindow": ([], H),
            "IsWindow": ([H], B),
            "IsWindowVisible": ([H], B),
            "IsWindowEnabled": ([H], B),
            "IsIconic": ([H], B),
            "GetWindowTextLengthW": ([H], ctypes.c_int),
            "GetWindowTextW": ([H, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetClassNameW": ([H, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetWindowRect": ([H, ctypes.POINTER(wintypes.RECT)], B),
            "GetWindowThreadProcessId": ([H, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            "GetForegroundWindow": ([], H),
            "GetGUIThreadInfo": ([wintypes.DWORD, ctypes.POINTER(_GUITHREADINFO)], B),
            "GetCursorPos": ([ctypes.POINTER(wintypes.POINT)], B),
            "SetCursorPos": ([ctypes.c_int, ctypes.c_int], B),
            "WindowFromPoint": ([wintypes.POINT], H),
            "ScreenToClient": ([H, ctypes.POINTER(wintypes.POINT)], B),
            "mouse_event": ([wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                             wintypes.DWORD, ctypes.c_size_t], None),
            "SendMessageTimeoutW": ([H, U, wintypes.WPARAM, wintypes.LPARAM, U, U,
                                     ctypes.POINTER(ctypes.c_ssize_t)], ctypes.c_ssize_t),
            "PostMessageW": ([H, U, wintypes.WPARAM, wintypes.LPARAM], B),
            "SetForegroundWindow": ([H], B),
            "SetFocus": ([H], H),
            "ShowWindow": ([H, ctypes.c_int], B),
            "AttachThreadInput": ([wintypes.DWORD, wintypes.DWORD, B], B),
            "GetDlgCtrlID": ([H], ctypes.c_int),
        }
        for name, (argtypes, restype) in sig.items():
            fn = getattr(u, name)
            fn.argtypes, fn.restype = argtypes, restype
        # GetWindowLongPtrW só existe em 64 bits; em 32 bits é GetWindowLongW.
        long_fn = getattr(u, "GetWindowLongPtrW", None)
        if long_fn is None:
            long_fn = u.GetWindowLongW
            long_fn.restype = ctypes.c_long
        else:
            long_fn.restype = ctypes.c_ssize_t
        long_fn.argtypes = [wintypes.HWND, ctypes.c_int]
        self._get_long = long_fn

    # ------------------------------------------------------------ enumeração
    def enum_top_level(self) -> list[int]:
        """Handles de todas as janelas de nível superior (em ordem Z)."""
        found: list[int] = []

        def callback(hwnd: int | None, _: int) -> bool:
            found.append(int(hwnd or 0))
            return True

        self._u.EnumWindows(self._enum_proc(callback), 0)
        return found

    def enum_descendants(self, hwnd: int) -> list[int]:
        """Todos os descendentes (filhos, netos...) de ``hwnd``."""
        found: list[int] = []

        def callback(child: int | None, _: int) -> bool:
            found.append(int(child or 0))
            return True

        self._u.EnumChildWindows(hwnd, self._enum_proc(callback), 0)
        return found

    def children(self, hwnd: int) -> list[int]:
        """Somente os filhos diretos de ``hwnd``."""
        out: list[int] = []
        seen: set[int] = set()
        child = self._u.GetWindow(hwnd, GW_CHILD)
        while child and child not in seen and len(out) < _MAX_CHILDREN:
            out.append(int(child))
            seen.add(int(child))
            child = self._u.GetWindow(child, GW_HWNDNEXT)
        return out

    # ---------------------------------------------------------- propriedades
    def is_window(self, hwnd: int) -> bool:
        return bool(hwnd) and bool(self._u.IsWindow(hwnd))

    def is_visible(self, hwnd: int) -> bool:
        return bool(self._u.IsWindowVisible(hwnd))

    def is_enabled(self, hwnd: int) -> bool:
        return bool(self._u.IsWindowEnabled(hwnd))

    def is_iconic(self, hwnd: int) -> bool:
        return bool(self._u.IsIconic(hwnd))

    def get_text(self, hwnd: int) -> str:
        """Texto via GetWindowTextW (rápido, não envia mensagens a outro processo)."""
        length = self._u.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        self._u.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_text_message(self, hwnd: int, timeout_ms: int = 300) -> str | None:
        """Texto via WM_GETTEXT (funciona em Edits de outros processos).

        Devolve ``None`` se a janela não responder dentro do prazo.
        """
        length = self.send_message(hwnd, WM_GETTEXTLENGTH, 0, 0, timeout_ms)
        if length is None:
            return None
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        done = self.send_message(hwnd, WM_GETTEXT, length + 1, ctypes.addressof(buf), timeout_ms)
        return None if done is None else buf.value

    def get_class_name(self, hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(257)
        self._u.GetClassNameW(hwnd, buf, 257)
        return buf.value

    def get_rect(self, hwnd: int) -> Rect:
        r = wintypes.RECT()
        if self._u.GetWindowRect(hwnd, ctypes.byref(r)):
            return Rect(r.left, r.top, r.right, r.bottom)
        return Rect()

    def parent_handle(self, hwnd: int) -> int:
        """Pai real (GA_PARENT); 0 para janelas de nível superior."""
        parent = int(self._u.GetAncestor(hwnd, GA_PARENT) or 0)
        return 0 if parent == self.desktop_hwnd else parent

    def owner_handle(self, hwnd: int) -> int:
        return int(self._u.GetWindow(hwnd, GW_OWNER) or 0)

    def root_handle(self, hwnd: int) -> int:
        return int(self._u.GetAncestor(hwnd, GA_ROOT) or 0)

    def thread_and_process(self, hwnd: int) -> tuple[int, int]:
        pid = wintypes.DWORD(0)
        tid = self._u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(tid), int(pid.value)

    def get_styles(self, hwnd: int) -> tuple[int, int]:
        """(WS_*, WS_EX_*) como inteiros sem sinal de 32 bits."""
        return (
            int(self._get_long(hwnd, GWL_STYLE)) & 0xFFFFFFFF,
            int(self._get_long(hwnd, GWL_EXSTYLE)) & 0xFFFFFFFF,
        )

    def control_id(self, hwnd: int) -> int:
        return int(self._u.GetDlgCtrlID(hwnd))

    # ---------------------------------------------------------------- foco
    def foreground_window(self) -> int:
        return int(self._u.GetForegroundWindow() or 0)

    def gui_thread_info(self, thread_id: int = 0) -> GuiThreadInfo | None:
        """Informações de GUI da thread (0 = thread em primeiro plano)."""
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not self._u.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            return None
        return GuiThreadInfo(
            active=int(info.hwndActive or 0), focus=int(info.hwndFocus or 0),
            capture=int(info.hwndCapture or 0), menu_owner=int(info.hwndMenuOwner or 0),
            move_size=int(info.hwndMoveSize or 0), caret=int(info.hwndCaret or 0),
        )

    def set_focus(self, hwnd: int, *, control: bool = True) -> bool:
        """Traz a janela raiz ao primeiro plano e, opcionalmente, foca o controle.

        Anexa temporariamente a fila de entrada da thread em primeiro plano,
        técnica necessária para o Windows permitir ``SetForegroundWindow``.
        """
        if not self.is_window(hwnd):
            return False
        root = self.root_handle(hwnd) or hwnd
        if self.is_iconic(root):
            self._u.ShowWindow(root, SW_RESTORE)
        fg_tid = self.thread_and_process(self.foreground_window())[0]
        target_tid = self.thread_and_process(root)[0]
        attached = bool(fg_tid and fg_tid != target_tid
                        and self._u.AttachThreadInput(fg_tid, target_tid, True))
        try:
            ok = bool(self._u.SetForegroundWindow(root))
            if control and hwnd != root:
                self._u.SetFocus(hwnd)
        finally:
            if attached:
                self._u.AttachThreadInput(fg_tid, target_tid, False)
        return ok

    # --------------------------------------------------------------- mouse
    def cursor_pos(self) -> tuple[int, int]:
        pt = wintypes.POINT()
        self._u.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_cursor_pos(self, x: int, y: int) -> None:
        self._u.SetCursorPos(int(x), int(y))

    def window_from_point(self, x: int, y: int) -> int:
        return int(self._u.WindowFromPoint(wintypes.POINT(int(x), int(y))) or 0)

    def screen_to_client(self, hwnd: int, x: int, y: int) -> tuple[int, int]:
        pt = wintypes.POINT(int(x), int(y))
        self._u.ScreenToClient(hwnd, ctypes.byref(pt))
        return pt.x, pt.y

    def mouse_button(self, button: str, down: bool) -> None:
        """Pressiona (``down=True``) ou solta um botão na posição atual."""
        try:
            flags = MOUSEEVENTF[button]
        except KeyError:
            raise ValueError(f"Botão inválido: {button!r}") from None
        self._u.mouse_event(flags[0] if down else flags[1], 0, 0, 0, 0)

    def mouse_click(self, x: int, y: int, button: str = "left",
                    double: bool = False, pause: float = 0.05) -> None:
        self.set_cursor_pos(x, y)
        for _ in range(2 if double else 1):
            self.mouse_button(button, True)
            self.mouse_button(button, False)
            if double:
                time.sleep(pause)

    # ----------------------------------------------------------- mensagens
    def send_message(self, hwnd: int, msg: int, wparam: int = 0, lparam: int = 0,
                     timeout_ms: int = 300) -> int | None:
        """SendMessageTimeoutW; ``None`` em timeout/falha (não trava o chamador)."""
        result = ctypes.c_ssize_t(0)
        ok = self._u.SendMessageTimeoutW(
            hwnd, msg, wparam, lparam, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result)
        )
        return int(result.value) if ok else None

    def post_message(self, hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> bool:
        return bool(self._u.PostMessageW(hwnd, msg, wparam, lparam))

    def notify_parent(self, hwnd: int, code: int) -> bool:
        """Envia WM_COMMAND ao pai, como o Windows faz ao mudar seleção/clicar."""
        parent = int(self._u.GetParent(hwnd) or 0)
        if not parent:
            return False
        wparam = ((code & 0xFFFF) << 16) | (self.control_id(hwnd) & 0xFFFF)
        return self.post_message(parent, WM_COMMAND, wparam, hwnd)


_instance: Win32 | None = None


def get_win32() -> Win32:
    """Instância compartilhada (as assinaturas são declaradas uma única vez)."""
    global _instance
    if _instance is None:
        _instance = Win32()
    return _instance
