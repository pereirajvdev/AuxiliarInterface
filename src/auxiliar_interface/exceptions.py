"""Exceções da biblioteca e utilitário para capturar erros de backends de terceiros."""

from __future__ import annotations

from functools import lru_cache


class AuxiliarInterfaceError(Exception):
    """Erro base de toda a biblioteca."""


class PlatformNotSupportedError(AuxiliarInterfaceError):
    """A funcionalidade exige Windows."""


class BackendUnavailableError(AuxiliarInterfaceError):
    """Uma dependência opcional (pywinauto, comtypes) não está instalada."""


class InvalidCriteriaError(AuxiliarInterfaceError, ValueError):
    """Critérios de busca inválidos (por exemplo, regex malformada)."""


class ElementNotFoundError(AuxiliarInterfaceError, LookupError):
    """Nenhuma janela ou controle satisfaz os critérios."""


class AmbiguousMatchError(AuxiliarInterfaceError):
    """Mais de um elemento satisfaz os critérios e ``Settings.strict`` está ativo."""


class InvalidHandleError(AuxiliarInterfaceError, ValueError):
    """O handle informado não corresponde a uma janela existente."""


class ElementStateError(AuxiliarInterfaceError):
    """O elemento existe, mas não está em estado adequado (invisível, desabilitado...)."""


class AutomationTimeoutError(AuxiliarInterfaceError, TimeoutError):
    """Tempo esgotado aguardando uma condição."""


class Win32Error(AuxiliarInterfaceError):
    """Falha em uma chamada da API Win32."""


class MsaaError(AuxiliarInterfaceError):
    """Falha ao consultar a interface MSAA (IAccessible)."""


@lru_cache(maxsize=1)
def backend_errors() -> tuple[type[BaseException], ...]:
    """Erros esperados ao consultar objetos de pywinauto/comtypes.

    Elementos podem desaparecer entre a enumeração e a consulta; nesses casos
    as bibliotecas levantam exceções variadas. Esta tupla permite capturá-las
    de forma específica, sem recorrer a ``except Exception``.
    """
    errors: list[type[BaseException]] = [
        OSError, ValueError, TypeError, AttributeError, LookupError,
        NotImplementedError, RuntimeError,
    ]
    try:
        from comtypes import COMError  # type: ignore[import-not-found]
        errors.append(COMError)
    except ImportError:
        pass
    try:
        import pywintypes  # type: ignore[import-not-found]
        errors.append(pywintypes.error)
    except ImportError:
        pass
    return tuple(errors)
