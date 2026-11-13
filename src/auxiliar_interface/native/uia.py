"""UI Automation via pywinauto: backend de descoberta e leitura de propriedades.

Nada aqui é executado na importação; ``pywinauto`` só é carregado quando um
recurso UIA é realmente usado. Propriedades que o aplicativo não publica via
UIA simplesmente não aparecem: a biblioteca não as inventa.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..config import Settings
from ..core.models import ElementInfo, Rect
from ..exceptions import BackendUnavailableError, backend_errors
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .win32 import Win32

log = get_logger("uia")

# Propriedades "IsXPatternAvailable" do UI Automation (valores documentados pela
# Microsoft, consecutivos em ordem alfabética a partir de 30027).
UIA_PATTERN_PROPERTY_IDS: dict[str, int] = {
    "Dock": 30027, "ExpandCollapse": 30028, "GridItem": 30029, "Grid": 30030,
    "Invoke": 30031, "MultipleView": 30032, "RangeValue": 30033, "Scroll": 30034,
    "ScrollItem": 30035, "SelectionItem": 30036, "Selection": 30037,
    "Table": 30038, "TableItem": 30039, "Text": 30040, "Toggle": 30041,
    "Transform": 30042, "Value": 30043, "Window": 30044,
    "LegacyIAccessible": 30090, "ItemContainer": 30108, "VirtualizedItem": 30109,
}

_COM_PROPERTIES = (
    "CurrentName", "CurrentLocalizedControlType", "CurrentControlType",
    "CurrentAutomationId", "CurrentClassName", "CurrentFrameworkId",
    "CurrentHelpText", "CurrentAcceleratorKey", "CurrentAccessKey",
    "CurrentItemStatus", "CurrentIsControlElement", "CurrentIsContentElement",
    "CurrentIsEnabled", "CurrentIsOffscreen", "CurrentNativeWindowHandle",
)


def load_pywinauto() -> Any:
    """Importa ``pywinauto`` sob demanda, com mensagem clara se faltar."""
    try:
        import pywinauto
    except ImportError as exc:
        raise BackendUnavailableError(
            "pywinauto não está instalado (pip install pywinauto)."
        ) from exc
    return pywinauto


def wrapper_for_handle(handle: int, backend: str) -> Any:
    """Cria o wrapper pywinauto (``win32`` ou ``uia``) para um HWND existente."""
    load_pywinauto()
    if backend == "uia":
        from pywinauto.controls.uiawrapper import UIAWrapper
        from pywinauto.uia_element_info import UIAElementInfo
        return UIAWrapper(UIAElementInfo(handle))
    from pywinauto.controls.hwndwrapper import HwndWrapper
    return HwndWrapper(handle)


def uia_properties(wrapper: Any) -> dict[str, Any]:
    """Propriedades UIA de um wrapper, incluindo padrões de acessibilidade.

    Cada leitura que falha vira ``"<indisponível: motivo>"`` em vez de abortar.
    """
    errors = backend_errors()
    info = wrapper.element_info
    props: dict[str, Any] = {}
    for name in ("name", "class_name", "control_type", "automation_id",
                 "framework_id", "handle", "process_id", "visible", "enabled"):
        try:
            props[name] = getattr(info, name)
        except errors as exc:
            props[name] = f"<indisponível: {exc}>"
    try:
        element = info.element
    except errors as exc:
        props["com_element"] = f"<indisponível: {exc}>"
        return props
    props["com_element_type"] = type(element).__name__
    for name in _COM_PROPERTIES:
        try:
            props[name] = getattr(element, name)
        except errors as exc:
            props[name] = f"<indisponível: {exc}>"
    patterns: list[str] = []
    for pattern, prop_id in UIA_PATTERN_PROPERTY_IDS.items():
        try:
            if element.GetCurrentPropertyValue(prop_id):
                patterns.append(pattern)
        except errors as exc:
            log.debug("Padrão %s indisponível: %s", pattern, exc)
    props["patterns"] = patterns
    return props


class UiaBackend:
    """Backend UIA. A hierarquia vem do pywinauto; elementos sem HWND são suportados."""

    name = "uia"

    def __init__(self, win32: "Win32 | None", settings: Settings | None = None) -> None:
        self.win32 = win32
        self.settings = settings or Settings(backend="uia")
        self._desktop: Any = None

    # ------------------------------------------------------------- helpers
    def _get_desktop(self) -> Any:
        if self._desktop is None:
            load_pywinauto()
            from pywinauto import Desktop
            self._desktop = Desktop(backend="uia")  # criado uma única vez
        return self._desktop

    def _to_info(self, wrapper: Any) -> ElementInfo | None:
        errors = backend_errors()
        try:
            ei = wrapper.element_info
            r = ei.rectangle
            handle = int(ei.handle or 0)
            return ElementInfo(
                handle=handle,
                title=ei.name or "",
                class_name=ei.class_name or "",
                rect=Rect(r.left, r.top, r.right, r.bottom),
                visible=bool(ei.visible),
                enabled=bool(ei.enabled),
                parent=self.win32.parent_handle(handle) if (self.win32 and handle) else 0,
                owner=self.win32.owner_handle(handle) if (self.win32 and handle) else 0,
                process_id=int(ei.process_id or 0),
                automation_id=ei.automation_id or "",
                control_type=str(ei.control_type or ""),
                native=wrapper,
            )
        except errors as exc:  # o elemento pode ter desaparecido
            log.debug("Elemento UIA ignorado: %s", exc)
            return None

    def _infos(self, wrappers: list[Any]) -> list[ElementInfo]:
        return [i for i in (self._to_info(w) for w in wrappers) if i is not None]

    def wrapper(self, info: ElementInfo) -> Any:
        """Wrapper pywinauto de um ``ElementInfo`` (usa ``native`` ou o handle)."""
        if info.native is not None:
            return info.native
        return wrapper_for_handle(info.handle, "uia")

    # ------------------------------------------------------------ contrato
    def top_level(self) -> list[ElementInfo]:
        return self._infos(self._get_desktop().windows())

    def children(self, parent: ElementInfo) -> list[ElementInfo]:
        return self._infos(self.wrapper(parent).children())

    def descendants(self, parent: ElementInfo) -> list[ElementInfo]:
        return self._infos(self.wrapper(parent).descendants())

    def from_handle(self, handle: int) -> ElementInfo | None:
        if self.win32 is not None and not self.win32.is_window(handle):
            return None
        try:
            return self._to_info(wrapper_for_handle(handle, "uia"))
        except backend_errors() as exc:
            log.debug("Handle %s sem elemento UIA: %s", handle, exc)
            return None

    def refresh(self, info: ElementInfo) -> ElementInfo | None:
        if info.native is not None:
            return self._to_info(info.native)
        return self.from_handle(info.handle)

    def exists(self, info: ElementInfo) -> bool:
        if info.handle and self.win32 is not None and not self.win32.is_window(info.handle):
            return False
        return self.refresh(info) is not None

    def parent_or_owner(self, handle: int) -> int:
        if self.win32 is None:
            return 0
        return self.win32.parent_handle(handle) or self.win32.owner_handle(handle)

    def at_point(self, x: int, y: int) -> ElementInfo | None:
        # Resolve o HWND sob o cursor e o converte para UIA. Elementos internos
        # sem HWND (células de grade) exigem a árvore UIA/MSAA, não este atalho.
        if self.win32 is None:
            return None
        hwnd = self.win32.window_from_point(x, y)
        return self.from_handle(hwnd) if hwnd else None

    def focused(self) -> ElementInfo | None:
        if self.win32 is None:
            return None
        gui = self.win32.gui_thread_info()
        return self.from_handle(gui.focus) if gui and gui.focus else None

    def foreground(self) -> ElementInfo | None:
        if self.win32 is None:
            return None
        hwnd = self.win32.foreground_window()
        return self.from_handle(hwnd) if hwnd else None
