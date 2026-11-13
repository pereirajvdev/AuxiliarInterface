"""CLI organizada por grupos: windows, controls, focus, mouse, hints, diagnostics."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Callable, Sequence

from .api import DesktopAutomation
from .config import BACKENDS, FOCUS_POLICIES, Settings, TEXT_SOURCES
from .core.control import Control
from .core.locator import Criteria
from .core.models import Rect
from .core.window import Window
from .exceptions import (AuxiliarInterfaceError, ElementNotFoundError,
                         PlatformNotSupportedError)
from .inspection import diagnostics as diag
from .inspection.hierarchy import list_windows
from .inspection.hints import probe_hints
from .utils.formatting import Report
from .utils.logging import configure_logging

Handler = Callable[[argparse.Namespace, DesktopAutomation], "Report | None"]


def _int(text: str) -> int:
    return int(text, 0)  # aceita decimal e 0x...


def _pair(text: str) -> tuple[int, int]:
    try:
        a, b = text.split(",")
        return int(a), int(b)
    except ValueError:
        raise argparse.ArgumentTypeError("use o formato X,Y (ex.: 315,20)") from None


def _rect(text: str) -> Rect:
    try:
        left, top, right, bottom = (int(p) for p in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("use o formato ESQ,TOPO,DIR,BASE") from None
    return Rect(left, top, right, bottom)


# ------------------------------------------------------------- argumentos
def _common() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    g = p.add_argument_group("opções gerais")
    g.add_argument("--backend", choices=BACKENDS, help="win32 (padrão) ou uia")
    g.add_argument("--timeout", type=float, help="timeout padrão das esperas (s)")
    g.add_argument("--focus", choices=FOCUS_POLICIES, dest="focus_policy",
                   help="política de foco antes de interagir")
    g.add_argument("--text-source", choices=TEXT_SOURCES,
                   help="como ler títulos: fast, message ou auto")
    g.add_argument("--json", action="store_true", help="saída em JSON")
    g.add_argument("-v", "--verbose", action="count", default=0, help="mais logs (-vv = debug)")
    return p


def _add_window_args(p: argparse.ArgumentParser, *, scoped: bool) -> None:
    g = p.add_argument_group("janela" if scoped else "seleção de janelas")
    g.add_argument("--title", dest="w_title", help="título exato")
    g.add_argument("--title-contains", dest="w_title_contains", help="parte do título")
    g.add_argument("--title-re", dest="w_title_re", help="expressão regular do título")
    cls, hdl = ("--window-class", "--window-handle") if scoped else ("--class", "--handle")
    g.add_argument(cls, dest="w_class", help="classe da janela")
    g.add_argument(cls + "-re", dest="w_class_re", help="regex da classe da janela")
    g.add_argument(hdl, dest="w_handle", type=_int, help="handle da janela")
    g.add_argument("--window-index" if scoped else "--index", dest="w_index", type=int,
                   help="N-ésima janela encontrada (0 = primeira)")
    if not scoped:
        g.add_argument("--pid", dest="w_pid", type=int, help="id do processo")
        g.add_argument("--visible", dest="w_visible", action="store_const", const=True)
        g.add_argument("--hidden", dest="w_visible", action="store_const", const=False)


def _add_control_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("filtro de controles")
    g.add_argument("--class", dest="c_class", action="append", help="classe (repetível)")
    g.add_argument("--class-re", dest="c_class_re")
    g.add_argument("--text", dest="c_title", help="texto exato")
    g.add_argument("--text-contains", dest="c_title_contains")
    g.add_argument("--text-re", dest="c_title_re")
    g.add_argument("--handle", dest="c_handle", type=_int, help="handle do controle")
    g.add_argument("--visible", dest="c_visible", action="store_const", const=True)
    g.add_argument("--hidden", dest="c_visible", action="store_const", const=False)
    g.add_argument("--enabled", dest="c_enabled", action="store_const", const=True)
    g.add_argument("--disabled", dest="c_enabled", action="store_const", const=False)
    g.add_argument("--has-text", dest="c_has_text", action="store_const", const=True)
    g.add_argument("--no-text", dest="c_has_text", action="store_const", const=False,
                   help="somente controles sem texto")
    g.add_argument("--inside", dest="c_inside", type=_rect, metavar="E,T,D,B",
                   help="centro do controle dentro deste retângulo de tela")
    g.add_argument("--direct", action="store_true", help="somente filhos diretos")
    g.add_argument("--index", dest="c_index", type=int)


def _opts(args: argparse.Namespace, prefix: str, names: Sequence[str]) -> dict[str, Any]:
    out = {}
    for name in names:
        value = getattr(args, f"{prefix}_{name}", None)
        if value is not None:
            out[name] = value
    return out


def _window_criteria(args: argparse.Namespace) -> Criteria | None:
    kw = _opts(args, "w", ("title", "title_contains", "title_re", "class_re", "handle",
                           "visible", "index"))
    if getattr(args, "w_class", None):
        kw["class_name"] = args.w_class
    if getattr(args, "w_pid", None) is not None:
        kw["process_id"] = args.w_pid
    if "class_re" in kw:
        kw["class_name_re"] = kw.pop("class_re")
    return Criteria(**kw) if kw else None


def _control_criteria(args: argparse.Namespace) -> Criteria:
    kw = _opts(args, "c", ("title", "title_contains", "title_re", "class_re", "handle",
                           "visible", "enabled", "has_text", "inside", "index"))
    if "class_re" in kw:
        kw["class_name_re"] = kw.pop("class_re")
    classes = getattr(args, "c_class", None)
    if classes:
        kw["class_name"] = classes[0] if len(classes) == 1 else tuple(classes)
    return Criteria(**kw)


def _need_window(args: argparse.Namespace) -> Criteria:
    crit = _window_criteria(args)
    if crit is None:
        raise ValueError("Informe a janela (--title, --title-contains, --title-re, "
                         "--window-class ou --window-handle).")
    return crit


def _first_control(aux: DesktopAutomation, args: argparse.Namespace) -> Control:
    win = Window(aux.context, _need_window(args))
    return win.control(**_criteria_kwargs(_control_criteria(args)))


def _criteria_kwargs(c: Criteria) -> dict[str, Any]:
    import dataclasses
    return {f.name: getattr(c, f.name) for f in dataclasses.fields(c)
            if getattr(c, f.name) != f.default}


# --------------------------------------------------------------- handlers
def windows_list(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    infos = list_windows(aux.context, _window_criteria(args), hide_noise=not args.no_noise_filter,
                         include_untitled=args.untitled)
    return Report("Janelas abertas", {"total": len(infos), "windows": [i.to_dict() for i in infos]})


def windows_inspect(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    backend = aux.context.backend
    fg = backend.foreground()
    infos = list_windows(aux.context, _need_window(args))
    items = []
    for info in infos:
        d = info.to_dict()
        d["active"] = bool(fg and fg.handle == info.handle)
        d["children"] = len(backend.children(info))
        items.append(d)
    if not items:
        raise ElementNotFoundError("Nenhuma janela satisfaz os critérios.")
    return Report("Janelas encontradas", {"total": len(items), "windows": items})


def windows_tree(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return diag.hierarchy_report(aux.context, _window_criteria(args), windows=True,
                                 hide_noise=not args.no_noise_filter, include_untitled=args.untitled)


def controls_list(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    crit = _control_criteria(args)
    window = _window_criteria(args)
    if window is None:
        if crit.handle is None:
            raise ValueError("Informe a janela ou --handle do controle.")
        info = aux.context.backend.from_handle(crit.handle)
        found = [info] if info and crit.matches(info) else []
    else:
        root = Window(aux.context, window).resolve()
        pool = aux.context.backend.children(root) if args.direct else aux.context.backend.descendants(root)
        found = crit.select(pool)
    return Report("Controles", {"total": len(found), "controls": [i.to_dict() for i in found]})


def _controls_inspect(args: argparse.Namespace, aux: DesktopAutomation, sources: Sequence[str],
                      textual: bool) -> Report:
    if getattr(args, "sources", None):
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    return diag.controls_report(aux.context, _window_criteria(args), _control_criteria(args),
                                direct=args.direct, sources=sources,
                                accessibility=getattr(args, "accessibility", False),
                                textual_only=textual)


def controls_inspect(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return _controls_inspect(args, aux, ("native",), False)


def controls_properties(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return _controls_inspect(args, aux, ("native", "pywinauto"), not args.all)


def controls_tree(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return diag.hierarchy_report(aux.context, _need_window(args), max_depth=args.depth)


def controls_click(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    """INTERAÇÃO explícita: clica no controle (valida existência e estado)."""
    ctl = _first_control(aux, args)
    ctl.click(button="right" if args.right else "left", double=args.double,
              offset=args.offset, method=args.method, verify=not args.no_verify)
    return Report("Clique realizado", {"control": ctl.info.to_dict()})


def controls_hover(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    """INTERAÇÃO explícita: move o mouse sobre o controle e lê o Hint."""
    ctl = _first_control(aux, args)
    hints = ctl.hint(offset=args.offset, delay=args.delay)
    return Report("Hints", {"control": ctl.info.to_dict(), "hints": [h.to_dict() for h in hints]})


def focus_inspect(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return diag.focus_report(aux.context)


def focus_trace(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    """INTERAÇÃO explícita: pressiona TAB N vezes e registra o foco."""
    crit = _window_criteria(args)
    if crit is not None:
        Window(aux.context, crit).activate()
    steps = aux.focus.trace_tab(args.tabs, delay=args.delay)
    return Report("Trilha de foco (TAB)", {"steps": [
        {"tab": s.step, **(s.focus.to_dict() if s.focus else {"focus": None})} for s in steps]})


def _countdown(seconds: float) -> None:
    if seconds > 0:
        print(f"Posicione o mouse... lendo em {seconds:g}s", file=sys.stderr)
        time.sleep(seconds)


def mouse_inspect(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    _countdown(args.delay)
    return diag.mouse_report(aux.context, accessibility=args.accessibility)


def mouse_monitor(args: argparse.Namespace, aux: DesktopAutomation) -> None:
    print("Mova o mouse. Ctrl+C para parar.", file=sys.stderr)
    for s in diag.monitor_mouse(aux.context, interval=args.interval, max_samples=args.samples):
        print(f"X={s['x']:<5} Y={s['y']:<5} HWND={s['handle']:<10} Classe={s['class_name']!r}", flush=True)


def mouse_click(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    """INTERAÇÃO explícita: clica na posição informada (ou onde o cursor está)."""
    _countdown(args.delay)
    x, y = args.at if args.at else aux.mouse.position
    info = aux.context.backend.at_point(x, y)
    aux.mouse.click(x, y, button="right" if args.right else "left", double=args.double)
    return Report("Clique realizado", {"x": x, "y": y, "control": info.to_dict() if info else None})


def mouse_move(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    aux.mouse.move(args.x, args.y)
    return Report("Mouse movido", {"x": args.x, "y": args.y})


def hints_probe(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    """INTERAÇÃO explícita: percorre os controles com o mouse procurando Hints."""
    root = Window(aux.context, _need_window(args)).resolve()
    pool = aux.context.backend.children(root) if args.direct else aux.context.backend.descendants(root)
    controls = _control_criteria(args).select(pool)
    hints = probe_hints(aux.context, controls, delay=args.delay, include_hidden=args.include_hidden)
    return Report("Hints encontrados", {"controls_probed": len(controls), "total": len(hints),
                                        "hints": [h.to_dict() for h in hints]})


def diagnostics_window(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    return diag.window_report(aux.context, _need_window(args), descendants=not args.no_descendants,
                              accessibility=args.accessibility)


def diagnostics_uia(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    ctl = _control_criteria(args)
    return aux.diagnostics.uia(_need_window(args), ctl if _criteria_kwargs(ctl) else None, limit=args.limit)


def diagnostics_msaa(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    ctl = _control_criteria(args)
    return aux.diagnostics.msaa(_need_window(args), ctl if _criteria_kwargs(ctl) else None,
                                depth=args.depth, max_children=args.max_children)


def diagnostics_grid(args: argparse.Namespace, aux: DesktopAutomation) -> Report:
    kw: dict[str, Any] = dict(tab_title=args.tab_title, tab_class=args.tab_class,
                              use_win32=not args.no_win32, use_uia=not args.no_uia,
                              use_msaa=not args.no_msaa, msaa_depth=args.depth,
                              max_children=args.max_children, uia_limit=args.limit)
    if args.grid_class:
        kw["grid_classes"] = tuple(args.grid_class)
    return aux.diagnostics.grid(_need_window(args), **kw)


# ----------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py", description="AuxiliarInterface — investigar e automatizar interfaces Windows.")
    groups = parser.add_subparsers(dest="group", metavar="GRUPO", required=True)
    common = _common()

    def group(name: str, help_: str) -> Any:
        g = groups.add_parser(name, help=help_)
        return g.add_subparsers(dest="action", metavar="AÇÃO", required=True)

    def leaf(sub: Any, name: str, help_: str, func: Handler, *, windows: str | None = None,
             controls: bool = False) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_, parents=[common])
        if windows:
            _add_window_args(p, scoped=(windows == "scoped"))
        if controls:
            _add_control_args(p)
        p.set_defaults(func=func)
        return p

    w = group("windows", "janelas de nível superior")
    p = leaf(w, "list", "lista janelas", windows_list, windows="plain")
    for q in (p, leaf(w, "tree", "hierarquia pai/proprietária", windows_tree, windows="plain")):
        q.add_argument("--untitled", action="store_true", help="inclui janelas sem título")
        q.add_argument("--no-noise-filter", action="store_true", help="não oculta janelas de sistema")
    leaf(w, "inspect", "detalha as janelas encontradas", windows_inspect, windows="plain")

    c = group("controls", "controles de uma janela")
    leaf(c, "list", "lista controles", controls_list, windows="scoped", controls=True)
    leaf(c, "inspect", "detalha controles (texto, itens, estilos)", controls_inspect,
         windows="scoped", controls=True).add_argument(
        "--sources", help="native,pywinauto,uia,msaa (padrão: native)")
    pp = leaf(c, "properties", "propriedades textuais (Name/Text/Caption/Hint/Help...)",
              controls_properties, windows="scoped", controls=True)
    pp.add_argument("--all", action="store_true", help="mostra todas as propriedades")
    pp.add_argument("--sources", help="native,pywinauto,uia,msaa (padrão: native,pywinauto)")
    leaf(c, "tree", "árvore de controles", controls_tree, windows="scoped").add_argument(
        "--depth", type=int, help="profundidade máxima")
    ck = leaf(c, "click", "[INTERAÇÃO] clica em um controle", controls_click, windows="scoped", controls=True)
    ck.add_argument("--offset", type=_pair, help="X,Y relativo ao canto do controle")
    ck.add_argument("--double", action="store_true")
    ck.add_argument("--right", action="store_true")
    ck.add_argument("--method", choices=("input", "message", "invoke"), default="input")
    ck.add_argument("--no-verify", action="store_true", help="não confere se o ponto pertence ao controle")
    hv = leaf(c, "hover", "[INTERAÇÃO] move o mouse sobre o controle e lê o Hint",
              controls_hover, windows="scoped", controls=True)
    hv.add_argument("--offset", type=_pair, help="X,Y relativo ao canto do controle")
    hv.add_argument("--delay", type=float, help="espera pelo Hint (s)")

    f = group("focus", "foco de teclado")
    leaf(f, "inspect", "quem tem o foco agora", focus_inspect)
    ft = leaf(f, "trace", "[INTERAÇÃO] pressiona TAB e registra o foco", focus_trace, windows="plain")
    ft.add_argument("--tabs", type=int, default=10)
    ft.add_argument("--delay", type=float, default=0.3)

    m = group("mouse", "mouse")
    mi = leaf(m, "inspect", "controle sob o cursor", mouse_inspect)
    mi.add_argument("--delay", type=float, default=0.0, help="espera antes de ler (s)")
    mi.add_argument("--accessibility", action="store_true", help="inclui objeto MSAA sob o cursor")
    mm = leaf(m, "monitor", "acompanha o cursor", mouse_monitor)
    mm.add_argument("--interval", type=float, default=0.05)
    mm.add_argument("--samples", type=int, help="para após N amostras")
    mc = leaf(m, "click", "[INTERAÇÃO] clica", mouse_click)
    mc.add_argument("--at", type=_pair, help="X,Y (padrão: posição atual)")
    mc.add_argument("--delay", type=float, default=3.0)
    mc.add_argument("--double", action="store_true")
    mc.add_argument("--right", action="store_true")
    mv = leaf(m, "move", "[INTERAÇÃO] move o cursor", mouse_move)
    mv.add_argument("x", type=int)
    mv.add_argument("y", type=int)

    h = group("hints", "Hints / tooltips")
    hp = leaf(h, "probe", "[INTERAÇÃO] move o mouse por cada controle procurando Hints",
              hints_probe, windows="scoped", controls=True)
    hp.add_argument("--delay", type=float)
    hp.add_argument("--include-hidden", action="store_true")

    d = group("diagnostics", "diagnósticos somente leitura")
    dw = leaf(d, "window", "diagnóstico completo da janela", diagnostics_window, windows="plain")
    dw.add_argument("--no-descendants", action="store_true")
    dw.add_argument("--accessibility", action="store_true")
    du = leaf(d, "uia", "propriedades e padrões UIA", diagnostics_uia, windows="scoped", controls=True)
    du.add_argument("--limit", type=int, help="máximo de elementos")
    dm = leaf(d, "msaa", "árvore MSAA (IAccessible)", diagnostics_msaa, windows="scoped", controls=True)
    dm.add_argument("--depth", type=int, default=1)
    dm.add_argument("--max-children", type=int, default=50)
    dg = leaf(d, "grid", "TcxGrid/TcxGridSite: Win32 + UIA + MSAA", diagnostics_grid, windows="scoped")
    dg.add_argument("--tab-title", help="título do TTabSheet que contém a grade")
    dg.add_argument("--tab-class", default="TTabSheet")
    dg.add_argument("--grid-class", action="append", help="classe da grade (repetível)")
    dg.add_argument("--no-win32", action="store_true")
    dg.add_argument("--no-uia", action="store_true")
    dg.add_argument("--no-msaa", action="store_true")
    dg.add_argument("--depth", type=int, default=1, help="profundidade MSAA")
    dg.add_argument("--max-children", type=int, default=50)
    dg.add_argument("--limit", type=int, help="máximo de elementos UIA")
    return parser


def _default_factory(args: argparse.Namespace) -> DesktopAutomation:
    overrides = {k: getattr(args, k) for k in ("timeout", "focus_policy", "text_source")
                 if getattr(args, k, None) is not None}
    return DesktopAutomation(args.backend or "win32", settings=Settings(
        backend=args.backend or "win32", **overrides))


def main(argv: Sequence[str] | None = None, *,
         factory: Callable[[argparse.Namespace], DesktopAutomation] | None = None) -> int:
    """Executa a CLI. Códigos: 0 ok, 1 não encontrado, 2 uso/erro, 3 plataforma."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # consoles cp1252 não imprimem '└──'
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        aux = (factory or _default_factory)(args)
        result = args.func(args, aux)
    except ElementNotFoundError as exc:
        print(f"Não encontrado: {exc}", file=sys.stderr)
        return 1
    except PlatformNotSupportedError as exc:
        print(f"Plataforma não suportada: {exc}", file=sys.stderr)
        return 3
    except (AuxiliarInterfaceError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    if result is not None:
        print(result.to_json() if args.json else result.render())
    return 0
