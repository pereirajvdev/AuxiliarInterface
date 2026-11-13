"""AuxiliarInterface — caixa de ferramentas para investigar e automatizar interfaces Windows.

Uso::

    from auxiliar_interface import DesktopAutomation

    aux = DesktopAutomation(backend="win32")
    janela = aux.window(title="Form1")
    if janela.exists():
        janela.control(class_name="Button").click()
"""

from .api import DesktopAutomation
from .config import NoiseFilter, Settings
from .core.control import Control
from .core.locator import Criteria
from .core.models import ElementInfo, Rect
from .core.window import Window
from .exceptions import (AmbiguousMatchError, AuxiliarInterfaceError, AutomationTimeoutError,
                         BackendUnavailableError, ElementNotFoundError, ElementStateError,
                         InvalidCriteriaError, InvalidHandleError, MsaaError,
                         PlatformNotSupportedError, Win32Error)
from .utils.formatting import Report

__version__ = "1.0.0"

__all__ = [
    "DesktopAutomation", "Settings", "NoiseFilter", "Window", "Control", "Criteria",
    "ElementInfo", "Rect", "Report", "AuxiliarInterfaceError", "AmbiguousMatchError",
    "AutomationTimeoutError", "BackendUnavailableError", "ElementNotFoundError",
    "ElementStateError", "InvalidCriteriaError", "InvalidHandleError", "MsaaError",
    "PlatformNotSupportedError", "Win32Error", "__version__",
]
