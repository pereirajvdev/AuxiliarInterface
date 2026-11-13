"""Modelos de dados imutáveis compartilhados por todas as camadas."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class Rect:
    """Retângulo em coordenadas de tela (right/bottom exclusivos, como no Win32)."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.right) // 2, (self.top + self.bottom) // 2

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom

    def to_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True)
class ElementInfo:
    """Instantâneo das propriedades de uma janela/controle.

    ``handle`` é 0 para elementos UIA sem HWND (nesse caso ``native`` guarda o
    objeto do pywinauto e é a identidade do elemento).
    """

    handle: int
    title: str = ""
    class_name: str = ""
    rect: Rect = Rect()
    visible: bool = True
    enabled: bool = True
    parent: int = 0
    owner: int = 0
    process_id: int = 0
    thread_id: int = 0
    automation_id: str = ""
    control_type: str = ""
    native: Any = field(default=None, compare=False, repr=False)

    @property
    def has_text(self) -> bool:
        return bool(self.title.strip())

    @property
    def key(self) -> tuple[str, Any]:
        """Identidade estável do elemento dentro de uma enumeração."""
        if self.handle:
            return ("h", self.handle)
        return ("n", id(self.native))

    def replace(self, **changes: Any) -> "ElementInfo":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "handle": self.handle,
            "title": self.title,
            "class_name": self.class_name,
            "rect": f"({self.rect.left}, {self.rect.top}, {self.rect.right}, {self.rect.bottom})",
            "size": f"{self.rect.width}x{self.rect.height}",
            "visible": self.visible,
            "enabled": self.enabled,
            "parent": self.parent,
            "owner": self.owner,
            "process_id": self.process_id,
        }
        if self.automation_id:
            data["automation_id"] = self.automation_id
        if self.control_type:
            data["control_type"] = self.control_type
        return data
