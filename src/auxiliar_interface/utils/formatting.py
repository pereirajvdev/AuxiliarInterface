"""Formatação de informações para leitura humana e JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..core.models import ElementInfo, Rect
    from ..inspection.hierarchy import TreeNode


def format_handle(handle: int) -> str:
    return f"{handle} (0x{handle:X})"


def format_rect(rect: "Rect") -> str:
    return f"({rect.left}, {rect.top}, {rect.right}, {rect.bottom}) {rect.width}x{rect.height}"


def format_element(info: "ElementInfo", index: int | None = None) -> str:
    """Linha única descrevendo um elemento."""
    prefix = f"[{index}] " if index is not None else ""
    extra = ""
    if info.automation_id:
        extra += f" | auto_id={info.automation_id!r}"
    if info.control_type:
        extra += f" | tipo={info.control_type}"
    return (
        f"{prefix}texto={info.title!r} | classe={info.class_name!r} | "
        f"handle={info.handle} | rect={format_rect(info.rect)} | "
        f"visível={info.visible} | habilitado={info.enabled}{extra}"
    )


def default_label(info: "ElementInfo") -> str:
    text = info.title if info.title else "<sem texto>"
    return f"{text}  [{info.class_name}] #{info.handle}"


def render_tree(node: "TreeNode", label: Callable[["ElementInfo"], str] | None = None) -> str:
    """Desenha uma árvore com caracteres de caixa (├── / └──)."""
    label = label or default_label
    lines = [label(node.info)]

    def walk(children: list["TreeNode"], prefix: str) -> None:
        for i, child in enumerate(children):
            last = i == len(children) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{label(child.info)}")
            walk(child.children, prefix + ("    " if last else "│   "))

    walk(node.children, "")
    return "\n".join(lines)


class Text(str):
    """Texto multilinha que o ``Report`` imprime em bloco (ex.: uma árvore)."""


def _is_scalar(value: Any) -> bool:
    return not isinstance(value, (dict, list, tuple))


def _fmt(value: Any) -> str:
    return repr(value) if isinstance(value, str) else str(value)


def _render(value: Any, indent: int, out: list[str]) -> None:
    pad = "  " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, Text):
                out.append(f"{pad}{key}:")
                out.extend(f"{pad}  {line}" for line in item.splitlines())
            elif _is_scalar(item):
                out.append(f"{pad}{key}: {_fmt(item)}")
            elif not item:
                out.append(f"{pad}{key}: -")
            else:
                out.append(f"{pad}{key}:")
                _render(item, indent + 1, out)
    else:
        for i, item in enumerate(value):
            if _is_scalar(item):
                out.append(f"{pad}- {_fmt(item)}")
            elif isinstance(item, dict) and all(_is_scalar(v) for v in item.values()):
                out.append(f"{pad}[{i}] " + " | ".join(f"{k}={_fmt(v)}" for k, v in item.items()))
            else:
                out.append(f"{pad}[{i}]")
                _render(item, indent + 1, out)


@dataclass
class Report:
    """Resultado estruturado de um diagnóstico (texto legível ou JSON)."""

    title: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, **self.data}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def render(self) -> str:
        out = ["=" * 80, self.title, "=" * 80]
        _render(self.data, 0, out)
        return "\n".join(out)

    def __str__(self) -> str:
        return self.render()
