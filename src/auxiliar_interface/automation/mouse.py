"""Mouse: posição, movimento, cliques e arrastar."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..config import Settings

if TYPE_CHECKING:
    from ..native.win32 import Win32


class Mouse:
    """Operações de mouse em coordenadas absolutas de tela."""

    def __init__(self, win32: "Win32", settings: Settings) -> None:
        self._w = win32
        self._s = settings

    @property
    def position(self) -> tuple[int, int]:
        return self._w.cursor_pos()

    def move(self, x: int, y: int) -> None:
        self._w.set_cursor_pos(x, y)

    def handle_at(self, x: int | None = None, y: int | None = None) -> int:
        """HWND sob o ponto (padrão: sob o cursor); 0 se não houver."""
        if x is None or y is None:
            x, y = self.position
        return self._w.window_from_point(x, y)

    def click(self, x: int | None = None, y: int | None = None, *,
              button: str = "left", double: bool = False) -> None:
        """Clica em ``(x, y)``; sem coordenadas, clica onde o cursor está."""
        if x is None or y is None:
            x, y = self.position
        self._w.mouse_click(x, y, button, double, self._s.click_pause)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        self.click(x, y, double=True)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        self.click(x, y, button="right")

    def drag(self, start: tuple[int, int], end: tuple[int, int], *,
             button: str = "left", steps: int = 10, step_delay: float = 0.01) -> None:
        """Arrasta de ``start`` até ``end`` em ``steps`` movimentos intermediários."""
        steps = max(1, steps)
        self.move(*start)
        self._w.mouse_button(button, True)
        try:
            for i in range(1, steps + 1):
                self.move(start[0] + (end[0] - start[0]) * i // steps,
                          start[1] + (end[1] - start[1]) * i // steps)
                time.sleep(step_delay)
        finally:
            self._w.mouse_button(button, False)  # nunca deixa o botão preso
