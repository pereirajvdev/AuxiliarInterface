"""Teclado via ``pywinauto.keyboard`` (sintaxe SendKeys), com helpers testáveis."""

from __future__ import annotations

from ..config import Settings
from ..native.uia import load_pywinauto

_MODIFIERS = {"ctrl": "^", "control": "^", "alt": "%", "shift": "+"}
_SPECIAL_KEYS = {
    "enter": "{ENTER}", "return": "{ENTER}", "tab": "{TAB}", "esc": "{ESC}",
    "escape": "{ESC}", "backspace": "{BACKSPACE}", "delete": "{DELETE}",
    "del": "{DELETE}", "insert": "{INSERT}", "home": "{HOME}", "end": "{END}",
    "pageup": "{PGUP}", "pagedown": "{PGDN}", "up": "{UP}", "down": "{DOWN}",
    "left": "{LEFT}", "right": "{RIGHT}", "space": "{SPACE}",
    **{f"f{i}": f"{{F{i}}}" for i in range(1, 13)},
}
_ESCAPES = {c: "{" + c + "}" for c in "+^%~(){}"}


def escape_text(text: str) -> str:
    """Escapa caracteres especiais do SendKeys para digitar ``text`` literalmente."""
    return "".join(_ESCAPES.get(c, c) for c in text)


def key_token(key: str) -> str:
    """Converte um nome de tecla (``"tab"``, ``"F5"``, ``"a"``) para SendKeys."""
    lowered = key.lower()
    if lowered in _SPECIAL_KEYS:
        return _SPECIAL_KEYS[lowered]
    if len(key) == 1:
        return _ESCAPES.get(key, key)
    raise ValueError(f"Tecla desconhecida: {key!r}")


def build_hotkey(*keys: str) -> str:
    """Monta uma combinação: ``build_hotkey("ctrl", "shift", "s") == "^+s"``."""
    if not keys:
        raise ValueError("Informe ao menos uma tecla.")
    *mods, last = keys
    prefix = ""
    for mod in mods:
        try:
            prefix += _MODIFIERS[mod.lower()]
        except KeyError:
            raise ValueError(f"Modificador desconhecido: {mod!r}") from None
    return prefix + key_token(last)


class Keyboard:
    """Entrada de teclado global (vai para a janela em primeiro plano).

    Garanta o foco antes (``Control.focus()`` / ``Window.activate()``).
    """

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def _send(self, sequence: str) -> None:
        load_pywinauto()
        from pywinauto.keyboard import send_keys
        send_keys(sequence, pause=self._s.typing_interval, with_spaces=True,
                  with_tabs=True, with_newlines=True)

    def type_text(self, text: str) -> None:
        """Digita ``text`` literalmente."""
        if text:
            self._send(escape_text(text))

    def press(self, key: str, times: int = 1) -> None:
        """Pressiona uma tecla especial/comum ``times`` vezes."""
        if times < 1:
            raise ValueError("times deve ser >= 1")
        self._send(key_token(key) * times)

    def hotkey(self, *keys: str) -> None:
        """Executa uma combinação, ex.: ``hotkey("ctrl", "a")``."""
        self._send(build_hotkey(*keys))

    def select_all(self) -> None:
        self.hotkey("ctrl", "a")

    def clear(self) -> None:
        """Seleciona tudo e apaga (no controle com foco)."""
        self.select_all()
        self.press("delete")
