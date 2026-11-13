"""Critérios de busca reutilizáveis e combináveis para janelas e controles."""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence, Union

from ..exceptions import InvalidCriteriaError
from .models import ElementInfo, Rect

ClassSpec = Union[str, Sequence[str]]


def strip_accelerator(text: str) -> str:
    """Remove o '&' de atalho de captions (``"&OK"`` -> ``"OK"``); ``&&`` vira ``&``."""
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&")


@dataclass(frozen=True)
class Criteria:
    """Conjunto de condições; todas as informadas devem ser satisfeitas (AND).

    - ``title``: igual ao título (ignora o ``&`` de atalho dos captions Delphi/VB).
    - ``title_contains``: substring do título.
    - ``title_re`` / ``class_name_re``: expressão regular, avaliada com ``re.match``
      (mesma semântica do pywinauto).
    - ``class_name``: uma classe ou uma coleção de classes aceitas.
    - ``has_text``: ``True`` só com texto, ``False`` só sem texto.
    - ``inside``: o centro do elemento deve estar dentro deste ``Rect``.
    - ``at_point``: o retângulo do elemento deve conter este ponto de tela.
    - ``predicate``: função ``ElementInfo -> bool`` para casos especiais.
    - ``index``: escolhe o N-ésimo resultado (0 = primeiro) depois dos filtros.
    """

    title: str | None = None
    title_contains: str | None = None
    title_re: str | None = None
    class_name: ClassSpec | None = None
    class_name_re: str | None = None
    handle: int | None = None
    visible: bool | None = None
    enabled: bool | None = None
    has_text: bool | None = None
    process_id: int | None = None
    automation_id: str | None = None
    control_type: str | None = None
    inside: Rect | None = None
    at_point: tuple[int, int] | None = None
    predicate: Callable[[ElementInfo], bool] | None = None
    ignore_case: bool = False
    index: int | None = None

    def __post_init__(self) -> None:
        for name in ("title_re", "class_name_re"):
            pattern = getattr(self, name)
            if pattern is not None:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise InvalidCriteriaError(f"{name} inválida ({pattern!r}): {exc}") from exc
        if isinstance(self.class_name, (list, set, frozenset)):
            object.__setattr__(self, "class_name", tuple(self.class_name))
        if self.index is not None and self.index < 0:
            raise InvalidCriteriaError("index não pode ser negativo")

    # ------------------------------------------------------------------ uso
    @property
    def _flags(self) -> int:
        return re.IGNORECASE if self.ignore_case else 0

    def _norm(self, text: str) -> str:
        return text.casefold() if self.ignore_case else text

    def matches(self, info: ElementInfo) -> bool:
        """Verdadeiro se ``info`` satisfaz todas as condições informadas."""
        if self.handle is not None and info.handle != self.handle:
            return False
        if self.visible is not None and info.visible != self.visible:
            return False
        if self.enabled is not None and info.enabled != self.enabled:
            return False
        if self.process_id is not None and info.process_id != self.process_id:
            return False
        if self.has_text is not None and info.has_text != self.has_text:
            return False
        if self.class_name is not None and not self._match_class(info.class_name):
            return False
        if self.class_name_re is not None and not re.match(
            self.class_name_re, info.class_name, self._flags
        ):
            return False
        if self.automation_id is not None and info.automation_id != self.automation_id:
            return False
        if self.control_type is not None and info.control_type.casefold() != self.control_type.casefold():
            return False
        if not self._match_title(info.title):
            return False
        if self.inside is not None and not self.inside.contains(*info.rect.center):
            return False
        if self.at_point is not None and not info.rect.contains(*self.at_point):
            return False
        if self.predicate is not None and not self.predicate(info):
            return False
        return True

    def _match_class(self, class_name: str) -> bool:
        wanted = [self.class_name] if isinstance(self.class_name, str) else list(self.class_name or ())
        return any(self._norm(class_name) == self._norm(w) for w in wanted)

    def _match_title(self, title: str) -> bool:
        if self.title is not None:
            a, b = self._norm(title), self._norm(self.title)
            if a != b and strip_accelerator(a) != strip_accelerator(b):
                return False
        if self.title_contains is not None and self._norm(self.title_contains) not in self._norm(title):
            return False
        if self.title_re is not None and not re.match(self.title_re, title, self._flags):
            return False
        return True

    def select(self, candidates: Iterable[ElementInfo]) -> list[ElementInfo]:
        """Filtra ``candidates`` e aplica ``index`` (quando definido)."""
        found = [c for c in candidates if self.matches(c)]
        if self.index is None:
            return found
        return found[self.index:self.index + 1]

    # ----------------------------------------------------------- composição
    def with_(self, **changes: Any) -> "Criteria":
        """Cópia com campos alterados."""
        return dataclasses.replace(self, **changes)

    def __and__(self, other: "Criteria") -> "Criteria":
        """Combina dois critérios; valores conflitantes levantam erro."""
        merged: dict[str, Any] = {}
        for f in dataclasses.fields(self):
            a, b = getattr(self, f.name), getattr(other, f.name)
            default = f.default
            if a == default:
                merged[f.name] = b
            elif b == default or a == b:
                merged[f.name] = a
            elif f.name == "predicate":
                merged[f.name] = (lambda p, q: lambda i: p(i) and q(i))(a, b)
            else:
                raise InvalidCriteriaError(f"Critérios conflitantes em {f.name!r}: {a!r} != {b!r}")
        return Criteria(**merged)

    def describe(self) -> str:
        """Texto curto com os campos definidos (para mensagens de erro/log)."""
        parts = []
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if value != f.default and f.name != "ignore_case":
                parts.append(f"{f.name}={'<função>' if callable(value) else value!r}")
        return ", ".join(parts) or "(sem critérios)"
