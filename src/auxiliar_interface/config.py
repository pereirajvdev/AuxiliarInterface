"""Configuração central. Nada específico de um aplicativo deve ficar fora daqui."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.models import ElementInfo

BACKENDS = ("win32", "uia")
FOCUS_POLICIES = ("auto", "never", "force")
TEXT_SOURCES = ("fast", "message", "auto")


@dataclass(frozen=True)
class NoiseFilter:
    """Janelas de sistema/ruído que costumam poluir listagens.

    Os valores padrão vêm do filtro usado originalmente em ``listarJanelas``.
    Use ``NoiseFilter.none()`` para desativar.
    """

    titles: frozenset[str] = frozenset()
    substrings: tuple[str, ...] = ()
    substrings_ci: tuple[str, ...] = ()
    classes: frozenset[str] = frozenset()

    @classmethod
    def default(cls) -> "NoiseFilter":
        return cls(
            titles=frozenset({
                "lidDialog", "DataSetValidDialog", "Chart editor",
                "Editor de Cross-tab", "Dictionary editor", "Rich Edit",
                "Task Host Window", "CDA Server", "RadeonSoftware",
                "WUIconWindow", "OneDrive", "ad_msg_wnd", "Window",
                "Program Manager", "Default IME", "M",
            }),
            substrings=(
                "GDI+ Window", "C:\\Windows", "AMD", "Microsoft", "Realtek",
                "Bluetooth", "HiddenFax", ".NET-BroadcastEventWindow",
            ),
            substrings_ci=("cmd.exe",),
        )

    @classmethod
    def none(cls) -> "NoiseFilter":
        return cls()

    def is_noise(self, info: "ElementInfo") -> bool:
        title = info.title.strip()
        if title in self.titles or info.class_name in self.classes:
            return True
        if any(s in title for s in self.substrings):
            return True
        lowered = title.lower()
        return any(s.lower() in lowered for s in self.substrings_ci)


@dataclass
class Settings:
    """Parâmetros de comportamento compartilhados por toda a sessão."""

    backend: str = "win32"
    timeout: float = 10.0            # padrão de todas as esperas (s)
    poll_interval: float = 0.1       # intervalo entre tentativas (s)
    strict: bool = False             # True: critério ambíguo levanta erro
    focus_policy: str = "auto"       # auto | never | force
    click_pause: float = 0.05        # pausa entre eventos de mouse (s)
    typing_interval: float = 0.01    # pausa entre teclas (s)
    hint_delay: float = 1.0          # tempo parado sobre o controle p/ Hints (s)
    message_timeout_ms: int = 300    # timeout de SendMessage (evita travar)
    text_source: str = "auto"        # fast | message | auto (ver Win32Backend)
    noise_filter: NoiseFilter = field(default_factory=NoiseFilter.default)

    def __post_init__(self) -> None:
        if self.backend not in BACKENDS:
            raise ValueError(f"backend deve ser um de {BACKENDS}, não {self.backend!r}")
        if self.focus_policy not in FOCUS_POLICIES:
            raise ValueError(f"focus_policy deve ser um de {FOCUS_POLICIES}")
        if self.text_source not in TEXT_SOURCES:
            raise ValueError(f"text_source deve ser um de {TEXT_SOURCES}")
        if self.timeout < 0 or self.poll_interval <= 0:
            raise ValueError("timeout >= 0 e poll_interval > 0 são obrigatórios")
