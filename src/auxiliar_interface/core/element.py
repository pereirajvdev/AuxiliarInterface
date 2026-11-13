"""Base comum de ``Window`` e ``Control``: localização preguiçosa e esperas.

Um ``Element`` guarda *critérios*, não um handle fixo. O handle é resolvido na
primeira necessidade e revalidado depois (um handle morto dispara nova busca),
o que o torna imune ao fato de handles mudarem entre execuções.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import AmbiguousMatchError, ElementNotFoundError
from ..utils.logging import get_logger
from ..utils.waiting import wait_until
from .context import Context
from .locator import Criteria
from .models import ElementInfo, Rect

if TYPE_CHECKING:
    from .control import Control
    from .window import Window

log = get_logger("element")


class Element:
    """Referência preguiçosa a uma janela ou controle."""

    _label = "Elemento"

    def __init__(self, ctx: Context, criteria: Criteria | None = None, *,
                 scope: "Element | None" = None, direct: bool = False,
                 info: ElementInfo | None = None) -> None:
        if criteria is None and info is None:
            criteria = Criteria()
        self._ctx = ctx
        self._criteria = criteria
        self._scope = scope
        self._direct = direct
        self._pinned = info

    def __repr__(self) -> str:
        what = self._criteria.describe() if self._criteria else f"handle={self._pinned.handle if self._pinned else '?'}"
        return f"<{type(self).__name__} {what}>"

    # ----------------------------------------------------------- localização
    def _candidates(self) -> list[ElementInfo]:
        backend = self._ctx.backend
        if self._scope is None:
            return backend.top_level()
        parent = self._scope.resolve()
        return backend.children(parent) if self._direct else backend.descendants(parent)

    def _is_inside(self, info: ElementInfo) -> bool:
        """Confere se ``info`` pertence ao escopo (usado na busca por handle)."""
        assert self._scope is not None
        scope = self._scope.resolve()
        if not scope.handle or not info.handle:
            return True  # sem HWND não há como verificar
        if self._direct:
            return info.parent == scope.handle
        cur: ElementInfo | None = info
        for _ in range(256):
            if cur is None or not cur.parent:
                return False
            if cur.parent == scope.handle:
                return True
            cur = self._ctx.backend.from_handle(cur.parent)
        return False

    def _search(self) -> ElementInfo | None:
        crit = self._criteria
        assert crit is not None
        backend = self._ctx.backend
        if crit.handle is not None:  # busca direta, inclusive de controles filhos
            info = backend.from_handle(crit.handle)
            if info is None or not crit.matches(info):
                return None
            if self._scope is not None and not self._is_inside(info):
                return None
            return info
        matches = crit.select(self._candidates())
        if not matches:
            return None
        if len(matches) > 1:
            if self._ctx.settings.strict:
                raise AmbiguousMatchError(
                    f"{len(matches)} elementos satisfazem: {crit.describe()}")
            log.debug("%d elementos satisfazem %s; usando o primeiro.", len(matches), crit.describe())
        return matches[0]

    def find(self) -> ElementInfo | None:
        """Busca nova (ignora o handle em cache). ``None`` se não existir."""
        if self._criteria is None:
            return self._ctx.backend.refresh(self._pinned) if self._pinned else None
        self._pinned = self._search()
        return self._pinned

    def exists(self) -> bool:
        """Verdadeiro se o elemento existe agora."""
        return self.find() is not None

    def resolve(self) -> ElementInfo:
        """Instantâneo atual. Reaproveita o handle em cache enquanto ele for válido."""
        if self._pinned is not None:
            current = self._ctx.backend.refresh(self._pinned)
            if current is not None:
                self._pinned = current
                return current
            if self._criteria is None:
                raise ElementNotFoundError(f"{self._label} deixou de existir.")
        info = self._search() if self._criteria is not None else None
        if info is None:
            crit = self._criteria.describe() if self._criteria else "?"
            raise ElementNotFoundError(f"{self._label} não encontrado: {crit}")
        self._pinned = info
        return info

    # ------------------------------------------------------------ propriedades
    @property
    def info(self) -> ElementInfo:
        return self.resolve()

    @property
    def handle(self) -> int:
        return self.resolve().handle

    @property
    def title(self) -> str:
        return self.resolve().title

    @property
    def class_name(self) -> str:
        return self.resolve().class_name

    @property
    def rect(self) -> Rect:
        return self.resolve().rect

    def is_visible(self) -> bool:
        info = self.find()
        return bool(info and info.visible)

    def is_enabled(self) -> bool:
        info = self.find()
        return bool(info and info.enabled)

    # ----------------------------------------------------------------- esperas
    def _timeout(self, timeout: float | None) -> float:
        return self._ctx.settings.timeout if timeout is None else timeout

    def _wait(self, condition: Any, timeout: float | None, what: str) -> "Element":
        wait_until(condition, timeout=self._timeout(timeout),
                   interval=self._ctx.settings.poll_interval,
                   description=f"{self._label} {what} ({self._criteria.describe() if self._criteria else ''})")
        return self

    def wait_for_exists(self, timeout: float | None = None) -> "Element":
        return self._wait(self.exists, timeout, "existir")

    def wait_for_gone(self, timeout: float | None = None) -> "Element":
        return self._wait(lambda: not self.exists(), timeout, "desaparecer")

    def wait_for_visible(self, timeout: float | None = None) -> "Element":
        return self._wait(self.is_visible, timeout, "ficar visível")

    def wait_for_enabled(self, timeout: float | None = None) -> "Element":
        return self._wait(self.is_enabled, timeout, "ficar habilitado")

    # --------------------------------------------------------------- navegação
    def _wrap(self, info: ElementInfo) -> "Window | Control":
        from .control import Control
        from .window import Window
        cls = Window if (info.handle and not info.parent) else Control
        return cls(self._ctx, info=info)

    def controls(self, **criteria: Any) -> list["Control"]:
        """Todos os descendentes que satisfazem ``criteria`` (ver ``Criteria``)."""
        from .control import Control
        found = Criteria(**criteria).select(self._ctx.backend.descendants(self.resolve()))
        return [Control(self._ctx, info=i) for i in found]

    def children(self, **criteria: Any) -> list["Control"]:
        """Somente os filhos diretos que satisfazem ``criteria``."""
        from .control import Control
        found = Criteria(**criteria).select(self._ctx.backend.children(self.resolve()))
        return [Control(self._ctx, info=i) for i in found]

    def control(self, **criteria: Any) -> "Control":
        """Controle descendente (localizado de forma preguiçosa)."""
        from .control import Control
        return Control(self._ctx, Criteria(**criteria), scope=self)

    def parent(self) -> "Window | Control | None":
        info = self.resolve()
        if not info.parent:
            return None
        parent = self._ctx.backend.from_handle(info.parent)
        return self._wrap(parent) if parent else None

    def ancestors(self) -> list["Window | Control"]:
        """Pais do mais próximo ao mais distante."""
        out: list[Window | Control] = []
        node = self.parent()
        while node is not None and len(out) < 256:
            out.append(node)
            node = node.parent()
        return out
