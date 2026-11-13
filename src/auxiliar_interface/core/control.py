"""Controles: leitura de valores e interação segura (valida existência e estado)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..automation.actions import control_kind
from ..exceptions import ElementStateError, backend_errors
from .element import Element
from .models import ElementInfo

if TYPE_CHECKING:
    from ..inspection.hints import HintResult


class Control(Element):
    """Controle localizado dentro de uma janela (ou de outro controle)."""

    _label = "Controle"

    # --------------------------------------------------------------- leitura
    @property
    def kind(self) -> str:
        """``edit`` | ``combo`` | ``list`` | ``button`` | ``unknown`` (pela classe)."""
        return control_kind(self.resolve().class_name)

    def text(self) -> str:
        """Texto do controle via WM_GETTEXT (ou UIA, em elementos sem HWND)."""
        info = self.resolve()
        if info.handle:
            return self._ctx.ops.get_text(info.handle)
        return str(info.native.window_text()) if info.native is not None else info.title

    def texts(self) -> list[str]:
        """Texto do controle seguido dos itens (quando for combo/lista)."""
        info = self.resolve()
        out = [self.text()]
        if info.handle and control_kind(info.class_name) in ("combo", "list"):
            out += self._ctx.ops.items(info.handle, control_kind(info.class_name))
        return out

    def items(self) -> list[str]:
        """Itens de um ComboBox/ListBox."""
        info = self.resolve()
        kind = self._require_kind(info, ("combo", "list"))
        return self._ctx.ops.items(info.handle, kind)

    def value(self) -> Any:
        """Melhor valor disponível: texto (edit), item selecionado (combo/lista),
        estado (botão de marcação) ou texto genérico."""
        info = self.resolve()
        kind = control_kind(info.class_name)
        if not info.handle:
            return self.text()
        if kind in ("combo", "list"):
            idx = self._ctx.ops.selected_index(info.handle, kind)
            items = self._ctx.ops.items(info.handle, kind)
            return items[idx] if 0 <= idx < len(items) else self.text()
        if kind == "button":
            return self._ctx.ops.check_state(info.handle)
        return self.text()

    def check_state(self) -> str:
        info = self.resolve()
        return self._ctx.ops.check_state(self._require_handle(info))

    def is_checked(self) -> bool:
        return self.check_state() == "checked"

    def has_focus(self) -> bool:
        info = self.find()
        focus = self._ctx.focus.current()
        return bool(info and focus and focus.handle == info.handle)

    # -------------------------------------------------------------- validações
    @staticmethod
    def _require_handle(info: ElementInfo) -> int:
        if not info.handle:
            raise ElementStateError("Operação exige um elemento com HWND (backend win32).")
        return info.handle

    @staticmethod
    def _require_kind(info: ElementInfo, kinds: tuple[str, ...]) -> str:
        """Valida a classe do controle e devolve o tipo detectado."""
        kind = control_kind(info.class_name)
        if kind not in kinds:
            raise ElementStateError(
                f"Classe {info.class_name!r} (tipo {kind!r}) não suporta esta operação; esperado {kinds}.")
        return kind

    def _ready(self, *, need_enabled: bool = True) -> ElementInfo:
        """Existe, está visível (e habilitado)? Caso contrário, não interage."""
        info = self.resolve()
        if not info.visible:
            raise ElementStateError(f"{self._label} invisível: {info.class_name!r} #{info.handle}")
        if need_enabled and not info.enabled:
            raise ElementStateError(f"{self._label} desabilitado: {info.class_name!r} #{info.handle}")
        return info

    def _point(self, info: ElementInfo, offset: tuple[int, int] | None) -> tuple[int, int]:
        rect = info.rect
        if rect.is_empty:
            raise ElementStateError(f"{self._label} sem área visível (rect={rect.to_tuple()}).")
        if offset is None:
            return rect.center
        x, y = rect.left + offset[0], rect.top + offset[1]
        if not rect.contains(x, y):
            raise ValueError(f"offset {offset} fora do controle ({rect.width}x{rect.height}).")
        return x, y

    def _check_target(self, info: ElementInfo, x: int, y: int) -> None:
        """Garante que o ponto pertence ao controle (ou a um descendente dele)."""
        top = self._ctx.backend.at_point(x, y)
        if top is None or not info.handle or top.handle == info.handle:
            return
        cur: ElementInfo | None = top
        for _ in range(64):
            if cur is None or not cur.parent:
                break
            if cur.parent == info.handle:
                return
            cur = self._ctx.backend.from_handle(cur.parent)
        raise ElementStateError(
            f"O ponto ({x}, {y}) está coberto por {top.class_name!r} #{top.handle}, "
            f"não por {info.class_name!r} #{info.handle}. Use verify=False para ignorar.")

    # ------------------------------------------------------------------- ações
    def focus(self) -> bool:
        """Dá foco de teclado ao controle (INTERAÇÃO)."""
        return self._ctx.focus.set(self._ready())

    def click(self, *, button: str = "left", double: bool = False,
              offset: tuple[int, int] | None = None, method: str = "input",
              verify: bool = True) -> None:
        """Clica no controle.

        ``method``: ``"input"`` (mouse real, padrão), ``"message"`` (WM_*/BM_CLICK,
        sem mover o mouse) ou ``"invoke"`` (padrão Invoke do UIA).
        ``offset`` é relativo ao canto superior esquerdo do controle; sem ele,
        clica no centro.
        """
        info = self._ready()
        if method == "invoke":
            if info.native is None:
                raise ElementStateError("method='invoke' exige o backend uia.")
            info.native.invoke()
            return
        x, y = self._point(info, offset)
        if method == "message":
            self._ctx.ops.post_click(self._require_handle(info), x, y, button=button,
                                     double=double, kind=control_kind(info.class_name))
        elif method == "input":
            if verify:
                self._check_target(info, x, y)
            self._ctx.focus.ensure_foreground(info)
            self._ctx.mouse.click(x, y, button=button, double=double)
        else:
            raise ValueError(f"method inválido: {method!r}")

    def double_click(self, **kwargs: Any) -> None:
        self.click(double=True, **kwargs)

    def right_click(self, **kwargs: Any) -> None:
        self.click(button="right", **kwargs)

    def type_text(self, text: str, *, clear: bool = False) -> None:
        """Foca o controle e digita ``text`` (opcionalmente limpando antes)."""
        self.focus()
        if clear:
            self._ctx.keyboard.clear()
        self._ctx.keyboard.type_text(text)

    def set_text(self, text: str, *, method: str = "type") -> None:
        """Define o conteúdo: ``"type"`` (foca, limpa e digita — dispara eventos
        do aplicativo) ou ``"message"`` (WM_SETTEXT, sem simular teclado)."""
        if method == "type":
            self.type_text(text, clear=True)
        elif method == "message":
            self._ctx.ops.set_text(self._require_handle(self._ready()), text)
        else:
            raise ValueError(f"method inválido: {method!r}")

    def select(self, item: str | int, *, notify: bool = True) -> int:
        """Seleciona um item de ComboBox/ListBox por texto exato ou índice."""
        info = self._ready()
        kind = self._require_kind(info, ("combo", "list"))
        return self._ctx.ops.select(info.handle, kind, item, notify=notify)

    def set_checked(self, checked: bool = True) -> None:
        """Marca/desmarca uma opção; clica só se o estado atual for diferente."""
        info = self._ready()
        self._require_kind(info, ("button",))
        if (self.check_state() == "checked") == checked:
            return
        self.click(method="message")
        time.sleep(self._ctx.settings.click_pause)
        if (self.check_state() == "checked") != checked:
            raise ElementStateError("O estado da opção não mudou após o clique.")

    def check(self) -> None:
        self.set_checked(True)

    def uncheck(self) -> None:
        self.set_checked(False)

    def hint(self, offset: tuple[int, int] | None = None,
             delay: float | None = None) -> list["HintResult"]:
        """Move o mouse sobre o controle e devolve os Hints que aparecerem (INTERAÇÃO)."""
        from ..inspection.hints import probe_point
        info = self._ready(need_enabled=False)
        x, y = self._point(info, offset)
        return probe_point(self._ctx, info, x, y, delay=delay)

    def native_properties(self) -> dict[str, Any]:
        """Propriedades do wrapper pywinauto do backend atual."""
        from ..inspection.properties import pywinauto_properties
        try:
            return pywinauto_properties(self.resolve(), self._ctx.settings.backend)
        except backend_errors() as exc:
            return {"erro": str(exc)}
