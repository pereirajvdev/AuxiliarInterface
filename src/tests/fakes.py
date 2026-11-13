"""Backend e drivers falsos em memória para testar sem Windows."""

from __future__ import annotations

from auxiliar_interface.config import Settings
from auxiliar_interface.core.context import Context
from auxiliar_interface.core.models import ElementInfo, Rect


class FakeBackend:
    name = "fake"

    def __init__(self, elements: list[ElementInfo], foreground: int = 0, focused: int = 0):
        self.elements = {e.handle: e for e in elements}
        self.fg, self.fc = foreground, focused

    def remove(self, handle: int) -> None:
        self.elements.pop(handle, None)

    def add(self, info: ElementInfo) -> None:
        self.elements[info.handle] = info

    def top_level(self):
        return [e for e in self.elements.values() if not e.parent]

    def children(self, parent):
        return [e for e in self.elements.values() if e.parent == parent.handle]

    def descendants(self, parent):
        out = []
        for c in self.children(parent):
            out.append(c)
            out += self.descendants(c)
        return out

    def from_handle(self, handle):
        return self.elements.get(handle)

    def refresh(self, info):
        return self.elements.get(info.handle)

    def exists(self, info):
        return info.handle in self.elements

    def parent_or_owner(self, handle):
        e = self.elements.get(handle)
        return (e.parent or e.owner) if e else 0

    def at_point(self, x, y):
        hits = [e for e in self.elements.values() if e.rect.contains(x, y)]
        return hits[-1] if hits else None   # o último é o mais "profundo"

    def focused(self):
        return self.elements.get(self.fc)

    def foreground(self):
        return self.elements.get(self.fg)


class FakeMouse:
    def __init__(self):
        self.clicks = []
        self.position = (0, 0)

    def click(self, x=None, y=None, **kw):
        self.clicks.append((x, y, kw))

    def move(self, x, y):
        self.position = (x, y)


def el(handle, title="", cls="TPanel", parent=0, rect=(0, 0, 100, 50), visible=True,
       enabled=True, owner=0, pid=1):
    return ElementInfo(handle=handle, title=title, class_name=cls, rect=Rect(*rect),
                       visible=visible, enabled=enabled, parent=parent, owner=owner, process_id=pid)


def sample_elements():
    """Form1(1) com OK(2), Cancelar(3, desabilitado), Edit(4, sem texto), Oculto(5);
    Panel(6) contendo Edit(7). Janela 10 'Confirmar' pertence à 1."""
    return [
        el(1, "Form1", "TForm1", rect=(0, 0, 400, 300)),
        el(2, "&OK", "TBitBtn", parent=1, rect=(10, 10, 90, 40)),
        el(3, "Cancelar", "TBitBtn", parent=1, rect=(100, 10, 180, 40), enabled=False),
        el(4, "", "TEdit", parent=1, rect=(10, 60, 200, 90)),
        el(5, "Oculto", "TButton", parent=1, rect=(0, 0, 0, 0), visible=False),
        el(6, "", "TPanel", parent=1, rect=(210, 60, 390, 290)),
        el(7, "Nome", "TEdit", parent=6, rect=(220, 70, 380, 100)),
        el(10, "Confirmar", "TConfirmDlg", owner=1, rect=(50, 50, 250, 150)),
        el(11, "Notepad", "Notepad", rect=(500, 0, 900, 300)),
    ]


def make_ctx(elements=None, **settings):
    backend = FakeBackend(elements or sample_elements(), foreground=1, focused=4)
    mouse = FakeMouse()
    settings.setdefault("focus_policy", "never")
    settings.setdefault("timeout", 0.3)
    settings.setdefault("poll_interval", 0.02)
    ctx = Context(Settings(**settings), backend=backend, mouse=mouse)
    return ctx, backend, mouse
