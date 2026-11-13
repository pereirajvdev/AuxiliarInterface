"""Árvores de janelas (pai/proprietária) e de controles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterator

from ..core.locator import Criteria
from ..core.models import ElementInfo
from ..utils.formatting import render_tree

if TYPE_CHECKING:
    from ..core.context import Context


@dataclass
class TreeNode:
    """Nó de uma árvore de elementos."""

    info: ElementInfo
    children: list["TreeNode"] = field(default_factory=list)

    def walk(self, depth: int = 0) -> Iterator[tuple[int, "TreeNode"]]:
        yield depth, self
        for child in self.children:
            yield from child.walk(depth + 1)

    def count(self) -> int:
        return sum(1 for _ in self.walk())

    def render(self, label: Callable[[ElementInfo], str] | None = None) -> str:
        return render_tree(self, label)

    def to_dict(self) -> dict[str, Any]:
        data = self.info.to_dict()
        if self.children:
            data["children"] = [c.to_dict() for c in self.children]
        return data


def build_control_tree(ctx: "Context", root: ElementInfo, *, max_depth: int | None = None) -> TreeNode:
    """Árvore de controles a partir de ``root`` (filhos diretos, recursivamente)."""
    seen = {root.key}

    def build(info: ElementInfo, depth: int) -> TreeNode:
        node = TreeNode(info)
        if max_depth is not None and depth >= max_depth:
            return node
        for child in ctx.backend.children(info):
            if child.key in seen:  # protege contra ciclos
                continue
            seen.add(child.key)
            node.children.append(build(child, depth + 1))
        return node

    return build(root, 0)


def list_windows(ctx: "Context", criteria: Criteria | None = None, *, hide_noise: bool = False,
                 include_untitled: bool = True) -> list[ElementInfo]:
    """Janelas de nível superior que satisfazem ``criteria``, sem repetições.

    ``hide_noise`` aplica ``Settings.noise_filter``; ``include_untitled=False``
    descarta janelas sem título.
    """
    criteria = criteria or Criteria()
    noise = ctx.settings.noise_filter
    seen: set[tuple[str, Any]] = set()
    out: list[ElementInfo] = []
    for info in ctx.backend.top_level():
        if info.key in seen or not criteria.matches(info):
            continue
        if not include_untitled and not info.title.strip():
            continue
        if hide_noise and noise.is_noise(info):
            continue
        seen.add(info.key)
        out.append(info)
    return out


def build_window_tree(ctx: "Context", criteria: Criteria | None = None, *,
                      hide_noise: bool = True, include_untitled: bool = False) -> list[TreeNode]:
    """Floresta de janelas de nível superior.

    Cada janela aparece uma vez. O pai é o pai real (``GA_PARENT``) ou, na falta
    dele, a proprietária (``GW_OWNER``); a cadeia sobe até achar um ancestral que
    também esteja na listagem (como em ``listarJanelas`` original).
    """
    nodes: dict[int, TreeNode] = {}
    order: list[int] = []
    for info in list_windows(ctx, criteria, hide_noise=hide_noise, include_untitled=include_untitled):
        if info.handle:
            nodes[info.handle] = TreeNode(info)
            order.append(info.handle)

    def resolve_parent(handle: int) -> int | None:
        visited = {handle}
        candidate = ctx.backend.parent_or_owner(handle)
        while candidate and candidate not in visited:
            if candidate in nodes:
                return candidate
            visited.add(candidate)
            candidate = ctx.backend.parent_or_owner(candidate)
        return None

    roots: list[TreeNode] = []
    for handle in order:
        parent = resolve_parent(handle)
        (nodes[parent].children if parent is not None else roots).append(nodes[handle])
    return roots
