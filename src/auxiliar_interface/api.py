"""API pública: ``DesktopAutomation``."""

from __future__ import annotations

from typing import Any

from .automation.focus import FocusManager
from .automation.keyboard import Keyboard
from .automation.mouse import Mouse
from .config import Settings
from .core.context import Context
from .core.control import Control
from .core.locator import Criteria
from .core.window import Window
from .inspection.diagnostics import Diagnostics, controls_report, focus_report, hierarchy_report, mouse_report, window_report
from .inspection.hierarchy import TreeNode, build_window_tree
from .utils.formatting import Report
from .utils.waiting import wait_until


class DesktopAutomation:
    """Ponto de entrada para localizar, inspecionar e automatizar aplicativos Windows.

    >>> aux = DesktopAutomation(backend="win32")          # doctest: +SKIP
    >>> janela = aux.window(title="Form1")                # doctest: +SKIP
    >>> janela.control(class_name="TBitBtn", title="&OK").click()  # doctest: +SKIP

    Parâmetros opcionais (``timeout``, ``strict``, ``focus_policy``, ``text_source``...)
    são repassados a ``Settings``; ou passe um ``Settings`` pronto em ``settings``.
    """

    def __init__(self, backend: str = "win32", *, settings: Settings | None = None,
                 context: Context | None = None, **options: Any) -> None:
        if context is not None:
            self.context = context
        else:
            self.context = Context(settings or Settings(backend=backend, **options))

    @property
    def settings(self) -> Settings:
        return self.context.settings

    # -------------------------------------------------------------- janelas
    def window(self, **criteria: Any) -> Window:
        """Janela (localização preguiçosa). Critérios: ver ``Criteria``."""
        return Window(self.context, Criteria(**criteria))

    def windows(self, **criteria: Any) -> list[Window]:
        """Todas as janelas de nível superior que satisfazem os critérios."""
        found = Criteria(**criteria).select(self.context.backend.top_level())
        return [Window(self.context, info=i) for i in found]

    def active_window(self) -> Window | None:
        info = self.context.backend.foreground()
        return Window(self.context, info=info) if info else None

    def wait_for_window(self, timeout: float | None = None, **criteria: Any) -> Window:
        """Aguarda a janela existir e a devolve."""
        win = self.window(**criteria)
        win.wait_for_exists(timeout)
        return win

    def wait_for_window_gone(self, timeout: float | None = None, **criteria: Any) -> None:
        self.window(**criteria).wait_for_gone(timeout)

    def window_tree(self, *, hide_noise: bool = True, include_untitled: bool = False,
                    **criteria: Any) -> list[TreeNode]:
        """Hierarquia (pai/proprietária) das janelas abertas."""
        return build_window_tree(self.context, Criteria(**criteria), hide_noise=hide_noise,
                                 include_untitled=include_untitled)

    # ---------------------------------------------------- controle / foco
    def control_at(self, x: int | None = None, y: int | None = None) -> Control | None:
        """Controle sob ``(x, y)`` (padrão: sob o cursor)."""
        if x is None or y is None:
            x, y = self.context.mouse.position
        info = self.context.backend.at_point(x, y)
        return Control(self.context, info=info) if info else None

    def focused_control(self) -> Control | None:
        info = self.context.focus.current()
        return Control(self.context, info=info) if info else None

    def wait_for_focus_change(self, timeout: float | None = None) -> Control:
        return Control(self.context, info=self.context.focus.wait_for_change(timeout=timeout))

    def wait_until(self, condition: Any, timeout: float | None = None, description: str = "condição") -> Any:
        """Utilitário genérico de espera usando os timeouts configurados."""
        return wait_until(condition, timeout=self.settings.timeout if timeout is None else timeout,
                          interval=self.settings.poll_interval, description=description)

    @property
    def mouse(self) -> Mouse:
        return self.context.mouse

    @property
    def keyboard(self) -> Keyboard:
        return self.context.keyboard

    @property
    def focus(self) -> FocusManager:
        return self.context.focus

    @property
    def diagnostics(self) -> Diagnostics:
        return Diagnostics(self.context)

    # ------------------------------------------------ diagnósticos (PT-BR)
    # Atalhos para as chamadas usadas na especificação do projeto.
    def diagnosticar_janela(self, title: str | None = None, **criteria: Any) -> Report:
        crit = Criteria(title=title, **criteria) if title is not None else Criteria(**criteria)
        return window_report(self.context, crit)

    def diagnosticar_controle(self, handle: int | None = None, *, window: Criteria | None = None,
                              **criteria: Any) -> Report:
        crit = Criteria(handle=handle, **criteria) if handle is not None else Criteria(**criteria)
        return controls_report(self.context, window, crit, sources=("native", "pywinauto"), accessibility=True)

    def diagnosticar_foco(self) -> Report:
        return focus_report(self.context)

    def diagnosticar_mouse(self) -> Report:
        return mouse_report(self.context)

    def diagnosticar_hierarquia(self, title: str | None = None, **criteria: Any) -> Report:
        crit = Criteria(title=title, **criteria) if title is not None else Criteria(**criteria)
        return hierarchy_report(self.context, crit)
