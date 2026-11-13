import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from auxiliar_interface import Criteria, DesktopAutomation, ElementNotFoundError
from auxiliar_interface.automation.actions import control_kind
from auxiliar_interface.automation.keyboard import build_hotkey, escape_text, key_token
from auxiliar_interface.cli import build_parser, main
from auxiliar_interface.config import NoiseFilter, Settings
from auxiliar_interface.inspection import diagnostics as diag
from auxiliar_interface.inspection.hierarchy import build_control_tree, build_window_tree, list_windows
from auxiliar_interface.inspection.properties import textual_properties
from auxiliar_interface.utils.formatting import Report, Text, format_element
from tests.fakes import el, make_ctx, sample_elements


class HierarchyTests(unittest.TestCase):
    def test_control_tree_and_depth(self):
        ctx, backend, _ = make_ctx()
        root = backend.from_handle(1)
        tree = build_control_tree(ctx, root)
        self.assertEqual(tree.count(), 7)
        self.assertEqual([n.info.handle for n in tree.children], [2, 3, 4, 5, 6])
        self.assertEqual(tree.children[4].children[0].info.handle, 7)
        shallow = build_control_tree(ctx, root, max_depth=1)
        self.assertEqual(shallow.count(), 6)

    def test_render_tree(self):
        ctx, backend, _ = make_ctx()
        text = build_control_tree(ctx, backend.from_handle(1)).render()
        self.assertIn("└── ", text)
        self.assertIn("├── ", text)
        self.assertIn("[TBitBtn] #2", text)

    def test_window_tree_owner_relation_and_noise(self):
        ctx, backend, _ = make_ctx()
        backend.add(el(12, "Microsoft Text Input", "X"))       # ruído
        backend.add(el(13, "Dialogo neto", "X", owner=10))      # pertence a 10, que pertence a 1
        roots = build_window_tree(ctx)
        by_handle = {r.info.handle: r for r in roots}
        self.assertEqual(set(by_handle), {1, 11})
        self.assertEqual([c.info.handle for c in by_handle[1].children], [10])
        self.assertEqual([c.info.handle for c in by_handle[1].children[0].children], [13])
        roots_all = build_window_tree(ctx, hide_noise=False)
        self.assertIn(12, {r.info.handle for r in roots_all})

    def test_window_tree_climbs_over_filtered_parent(self):
        ctx, _, _ = make_ctx()
        roots = build_window_tree(ctx, Criteria(title_re="Confirmar|Notepad"))
        self.assertEqual({r.info.handle for r in roots}, {10, 11})  # pai (1) filtrado => vira raiz

    def test_list_windows_untitled(self):
        ctx, backend, _ = make_ctx()
        backend.add(el(14, "", "Mudo"))
        self.assertIn(14, [i.handle for i in list_windows(ctx)])
        self.assertNotIn(14, [i.handle for i in list_windows(ctx, include_untitled=False)])

    def test_noise_filter_custom(self):
        nf = NoiseFilter(titles=frozenset({"A"}), substrings_ci=("cmd.exe",))
        self.assertTrue(nf.is_noise(el(1, "A")))
        self.assertTrue(nf.is_noise(el(1, "C:\\X\\CMD.EXE")))
        self.assertFalse(NoiseFilter.none().is_noise(el(1, "Microsoft")))
        self.assertTrue(NoiseFilter.default().is_noise(el(1, "Microsoft Foo")))


class FormattingTests(unittest.TestCase):
    def test_format_element(self):
        line = format_element(el(2, "&OK", "TBitBtn", rect=(10, 10, 90, 40)), 3)
        self.assertIn("[3]", line)
        self.assertIn("classe='TBitBtn'", line)
        self.assertIn("80x30", line)

    def test_report_render_and_json(self):
        r = Report("T", {"a": 1, "b": "x", "lista": [{"h": 1, "t": "y"}], "vazio": [],
                         "arv": Text("l1\nl2"), "aninhado": {"k": 2}})
        out = r.render()
        for expected in ("a: 1", "b: 'x'", "[0] h=1 | t='y'", "vazio: -", "  l2", "  k: 2"):
            self.assertIn(expected, out)
        self.assertEqual(json.loads(r.to_json())["lista"][0]["t"], "y")

    def test_textual_properties(self):
        props = {"class_name": "X", "texts": ["a"], "rect": "r", "empty_text": "  ", "hint": "dica",
                 "none_caption": None}
        self.assertEqual(set(textual_properties(props)), {"class_name", "texts", "hint"})


class KeyboardHelperTests(unittest.TestCase):
    def test_escape_and_keys(self):
        self.assertEqual(escape_text("a+b^c%(d){e}~"), "a{+}b{^}c{%}{(}d{)}{{}e{}}{~}")
        self.assertEqual(key_token("TAB"), "{TAB}")
        self.assertEqual(key_token("F5"), "{F5}")
        self.assertEqual(build_hotkey("ctrl", "a"), "^a")
        self.assertEqual(build_hotkey("ctrl", "shift", "tab"), "^+{TAB}")
        with self.assertRaises(ValueError):
            key_token("inexistente")
        with self.assertRaises(ValueError):
            build_hotkey("hyper", "a")
        with self.assertRaises(ValueError):
            build_hotkey()

    def test_control_kind(self):
        cases = {"ComboBox": "combo", "TelLookupCombo": "combo", "TListBox": "list",
                 "TCheckBox": "button", "TBitBtn": "button", "Button": "button",
                 "TcxCustomInnerTextEdit": "edit", "TPanel": "unknown"}
        for cls, kind in cases.items():
            self.assertEqual(control_kind(cls), kind, cls)

    def test_settings_validation(self):
        with self.assertRaises(ValueError):
            Settings(backend="x")
        with self.assertRaises(ValueError):
            Settings(focus_policy="x")


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.ctx, self.backend, self.mouse = make_ctx()
        self.aux = DesktopAutomation(context=self.ctx)

    def test_window_report(self):
        r = diag.window_report(self.ctx, Criteria(title="Form1")).to_dict()
        self.assertEqual(r["window"]["class_name"], "TForm1")
        self.assertTrue(r["active"])
        self.assertEqual(r["direct_children_count"], 5)
        self.assertEqual(r["descendants_count"], 6)
        self.assertEqual([t["text"] for t in r["texts"]], ["&OK", "Cancelar", "Oculto", "Nome"])
        self.assertEqual([w["handle"] for w in r["owned_windows"]], [10])

    def test_window_report_missing(self):
        with self.assertRaises(ElementNotFoundError):
            diag.window_report(self.ctx, Criteria(title="Nada"))

    def test_controls_report_by_handle_and_window(self):
        r = diag.controls_report(self.ctx, None, Criteria(handle=7), sources=()).to_dict()
        self.assertEqual(r["total"], 1)
        self.assertEqual([a["handle"] for a in r["controls"][0]["ancestors"]], [6, 1])
        r = diag.controls_report(self.ctx, Criteria(title="Form1"), Criteria(class_name="TEdit"),
                                 sources=()).to_dict()
        self.assertEqual(r["total"], 2)
        with self.assertRaises(ValueError):
            diag.controls_report(self.ctx, None, Criteria(class_name="TEdit"))

    def test_focus_and_mouse_reports_are_read_only(self):
        self.mouse.position = (15, 15)
        f = diag.focus_report(self.ctx).to_dict()
        self.assertEqual(f["focused_control"]["handle"], 4)
        m = diag.mouse_report(self.ctx).to_dict()
        self.assertEqual(m["control"]["handle"], 2)
        self.assertEqual(m["position"], {"x": 15, "y": 15})
        self.assertEqual(self.mouse.clicks, [])

    def test_monitor_mouse_yields_only_changes(self):
        self.mouse.position = (15, 15)
        samples = list(diag.monitor_mouse(self.ctx, interval=0.001, max_samples=1))
        self.assertEqual(samples[0]["handle"], 2)

    def test_hierarchy_reports(self):
        r = diag.hierarchy_report(self.ctx, Criteria(title="Form1")).to_dict()
        self.assertEqual(r["controls"], 6)
        self.assertIn("Form1", r["tree"])
        w = diag.hierarchy_report(self.ctx, None, windows=True).to_dict()
        self.assertEqual(w["windows"], 3)

    def test_portuguese_shortcuts(self):
        self.assertEqual(self.aux.diagnosticar_janela("Form1").to_dict()["window"]["handle"], 1)
        self.assertEqual(self.aux.diagnosticar_hierarquia("Form1").to_dict()["controls"], 6)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        ctx, _, mouse = make_ctx()
        mouse.position = (15, 15)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv), factory=lambda a: DesktopAutomation(context=ctx))
        return code, out.getvalue(), err.getvalue()

    def test_parser_examples_from_spec(self):
        p = build_parser()
        a = p.parse_args(["controls", "list", "--title", "Form1", "--backend", "win32"])
        self.assertEqual((a.w_title, a.backend), ("Form1", "win32"))
        a = p.parse_args(["windows", "list", "--visible"])
        self.assertTrue(a.w_visible)
        a = p.parse_args(["controls", "inspect", "--handle", "123456"])
        self.assertEqual(a.c_handle, 123456)
        a = p.parse_args(["controls", "inspect", "--handle", "0x10"])
        self.assertEqual(a.c_handle, 16)
        for cmd in (["windows", "inspect"], ["windows", "tree"], ["controls", "properties"],
                    ["focus", "inspect"], ["mouse", "inspect"], ["mouse", "monitor"],
                    ["diagnostics", "window"], ["diagnostics", "uia"], ["diagnostics", "msaa"],
                    ["diagnostics", "grid"]):
            self.assertTrue(hasattr(p.parse_args(cmd), "func"), cmd)

    def test_windows_list(self):
        code, out, _ = self.run_cli("windows", "list")
        self.assertEqual(code, 0)
        self.assertIn("title='Form1'", out)
        code, out, _ = self.run_cli("windows", "list", "--title-re", "Not.*", "--json")
        self.assertEqual([w["title"] for w in json.loads(out)["windows"]], ["Notepad"])

    def test_controls_list_filters(self):
        code, out, _ = self.run_cli("controls", "list", "--title", "Form1", "--class", "TEdit",
                                    "--no-text", "--json")
        self.assertEqual(code, 0)
        self.assertEqual([c["handle"] for c in json.loads(out)["controls"]], [4])
        code, out, _ = self.run_cli("controls", "list", "--handle", "7", "--json")
        self.assertEqual(json.loads(out)["total"], 1)

    def test_tree_and_diagnostics(self):
        code, out, _ = self.run_cli("windows", "tree")
        self.assertEqual(code, 0)
        self.assertIn("Confirmar", out)
        code, out, _ = self.run_cli("diagnostics", "window", "--title", "Form1")
        self.assertEqual(code, 0)
        self.assertIn("descendants_count: 6", out)

    def test_mouse_and_focus_inspect(self):
        code, out, _ = self.run_cli("mouse", "inspect")
        self.assertEqual(code, 0)
        self.assertIn("'TBitBtn'", out)
        code, out, _ = self.run_cli("focus", "inspect")
        self.assertIn("'TEdit'", out)

    def test_errors_and_exit_codes(self):
        code, _, err = self.run_cli("diagnostics", "window", "--title", "Nada")
        self.assertEqual(code, 1)
        self.assertIn("Não encontrado", err)
        code, _, err = self.run_cli("controls", "list")        # falta janela/handle
        self.assertEqual(code, 2)
        code, _, err = self.run_cli("windows", "list", "--title-re", "(")
        self.assertEqual(code, 2)
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["windows", "nada"])

    def test_click_requires_enabled_control(self):
        code, _, err = self.run_cli("controls", "click", "--title", "Form1", "--text", "Cancelar")
        self.assertEqual(code, 2)
        self.assertIn("desabilitado", err)


if __name__ == "__main__":
    unittest.main()
