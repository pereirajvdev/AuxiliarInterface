"""Contexto compartilhado: configurações + backend + drivers de entrada.

Os componentes são criados sob demanda (``cached_property``), de modo que
importar a biblioteca ou criar um ``Context`` com um backend falso não exige
Windows. Qualquer componente pode ser injetado no construtor (útil em testes).
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

from ..config import Settings
from .backend import Backend, make_backend

if TYPE_CHECKING:
    from ..automation.actions import ControlOps
    from ..automation.focus import FocusManager
    from ..automation.keyboard import Keyboard
    from ..automation.mouse import Mouse
    from ..native.msaa import MsaaClient
    from ..native.win32 import Win32


class Context:
    """Agrupa tudo o que janelas e controles precisam para trabalhar."""

    def __init__(self, settings: Settings | None = None, *, backend: Backend | None = None,
                 win32: "Win32 | None" = None, mouse: "Mouse | None" = None,
                 keyboard: "Keyboard | None" = None, focus: "FocusManager | None" = None,
                 ops: "ControlOps | None" = None, msaa: "MsaaClient | None" = None) -> None:
        self.settings = settings or Settings()
        injected: dict[str, Any] = {"backend": backend, "win32": win32, "mouse": mouse,
                                    "keyboard": keyboard, "focus": focus, "ops": ops,
                                    "msaa": msaa}
        for name, value in injected.items():
            if value is not None:
                self.__dict__[name] = value  # sobrepõe o cached_property

    @cached_property
    def win32(self) -> "Win32":
        from ..native.win32 import get_win32
        return get_win32()

    @cached_property
    def backend(self) -> Backend:
        return make_backend(self.settings.backend, self.win32, self.settings)

    @cached_property
    def mouse(self) -> "Mouse":
        from ..automation.mouse import Mouse
        return Mouse(self.win32, self.settings)

    @cached_property
    def keyboard(self) -> "Keyboard":
        from ..automation.keyboard import Keyboard
        return Keyboard(self.settings)

    @cached_property
    def focus(self) -> "FocusManager":
        from ..automation.focus import FocusManager
        return FocusManager(self)

    @cached_property
    def ops(self) -> "ControlOps":
        from ..automation.actions import ControlOps
        return ControlOps(self.win32, self.settings)

    @cached_property
    def msaa(self) -> "MsaaClient":
        from ..native.msaa import MsaaClient
        return MsaaClient()
