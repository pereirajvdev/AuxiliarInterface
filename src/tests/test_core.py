import threading
import time
import unittest

from auxiliar_interface import (AmbiguousMatchError, AutomationTimeoutError, DesktopAutomation,
                                ElementNotFoundError, ElementStateError)
from auxiliar_interface.core.control import Control
from auxiliar_interface.core.window import Window
from tests.fakes import el, make_ctx


def make_aux(**kw):
    ctx, backend, mouse = make_ctx(**kw)
    return DesktopAutomation(context=ctx), backend, mouse


class WindowTests(unittest.TestCase):
    def test_find_by_title_class_regex_handle(self):
        aux, _, _ = make_aux()
        self.assertEqual(aux.window(title="Form1").handle, 1)
        self.assertEqual(aux.window(title_contains="Note").handle, 11)
        self.assertEqual(aux.window(title_re=".*orm.*").handle, 1)
        self.assertEqual(aux.window(class_name="Notepad").title, "Notepad")
        self.assertEqual(aux.window(handle=10).title, "Confirmar")

    def test_handle_lookup_finds_child_controls_too(self):
        aux, _, _ = make_aux()
        self.assertEqual(aux.window(handle=2).class_name, "TBitBtn")

    def test_missing_window(self):
        aux, _, _ = make_aux()
        w = aux.window(title="Nada")
        self.assertFalse(w.exists())
        with self.assertRaises(ElementNotFoundError):
            _ = w.handle

    def test_list_windows_and_visibility(self):
        aux, backend, _ = make_aux()
        self.assertEqual({w.handle for w in aux.windows()}, {1, 10, 11})
        backend.add(el(12, "Oculta", "X", visible=False))
        self.assertEqual({w.handle for w in aux.windows(visible=False)}, {12})

    def test_active_owned_and_owner(self):
        aux, _, _ = make_aux()
        form = aux.window(title="Form1")
        self.assertTrue(form.is_active())
        self.assertFalse(aux.window(title="Notepad").is_active())
        self.assertEqual([w.handle for w in form.owned_windows()], [10])
        self.assertEqual(aux.window(title="Confirmar").owner().handle, 1)
        self.assertEqual(aux.active_window().handle, 1)

    def test_strict_ambiguity(self):
        aux, backend, _ = make_aux(strict=True)
        backend.add(el(20, "Form1", "TForm1"))
        with self.assertRaises(AmbiguousMatchError):
            aux.window(title="Form1").resolve()
        # com index explícito deixa de ser ambíguo
        self.assertEqual(aux.window(title="Form1", index=1).handle, 20)

    def test_handle_changes_between_runs(self):
        aux, backend, _ = make_aux()
        w = aux.window(title="Form1")
        self.assertEqual(w.handle, 1)
        backend.remove(1)           # janela foi fechada...
        backend.add(el(99, "Form1", "TForm1"))   # ...e reaberta com outro handle
        self.assertEqual(w.handle, 99)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.aux, self.backend, self.mouse = make_aux()
        self.form = self.aux.window(title="Form1")

    def test_listing_and_filters(self):
        self.assertEqual({c.handle for c in self.form.controls()}, {2, 3, 4, 5, 6, 7})
        self.assertEqual({c.handle for c in self.form.children()}, {2, 3, 4, 5, 6})
        self.assertEqual([c.handle for c in self.form.controls(class_name="TEdit")], [4, 7])
        self.assertEqual([c.handle for c in self.form.controls(has_text=False, class_name="TEdit")], [4])
        self.assertEqual([c.handle for c in self.form.controls(visible=False)], [5])
        self.assertEqual([c.handle for c in self.form.controls(enabled=False)], [3])
        self.assertEqual([c.handle for c in self.form.controls(handle=7)], [7])

    def test_title_with_accelerator_example_from_spec(self):
        self.assertEqual(self.form.control(class_name="TBitBtn", title="&OK").handle, 2)

    def test_parent_children_ancestors(self):
        edit = self.form.control(title="Nome")
        self.assertEqual(edit.parent().handle, 6)
        self.assertEqual([a.handle for a in edit.ancestors()], [6, 1])
        self.assertIsInstance(edit.ancestors()[-1], Window)
        self.assertIsInstance(edit.parent(), Control)

    def test_control_lookup_respects_scope_for_handle(self):
        panel = self.form.control(class_name="TPanel")
        self.assertTrue(panel.control(handle=7).exists())
        self.assertFalse(panel.control(handle=2).exists())

    def test_click_center_offset_and_guards(self):
        self.form.control(title="OK").click()
        self.assertEqual(self.mouse.clicks[-1][:2], (50, 25))
        self.form.control(title="OK").click(offset=(5, 5), double=True)
        x, y, kw = self.mouse.clicks[-1]
        self.assertEqual((x, y, kw["double"]), (15, 15, True))
        with self.assertRaises(ValueError):
            self.form.control(title="OK").click(offset=(500, 5))
        with self.assertRaises(ElementStateError):
            self.form.control(title="Cancelar").click()       # desabilitado
        with self.assertRaises(ElementStateError):
            self.form.control(title="Oculto").click()         # invisível
        with self.assertRaises(ElementNotFoundError):
            self.form.control(title="Inexistente").click()
        self.assertEqual(len(self.mouse.clicks), 2)           # nenhum clique indevido

    def test_click_blocked_when_point_covered(self):
        self.backend.add(el(30, "Cobertura", "TOverlay", parent=1, rect=(0, 0, 100, 50)))
        with self.assertRaises(ElementStateError):
            self.form.control(title="OK").click()
        self.form.control(title="OK").click(verify=False)
        self.assertEqual(len(self.mouse.clicks), 1)

    def test_click_on_vanished_control(self):
        ok = self.form.control(title="OK")
        ok.resolve()
        self.backend.remove(2)
        with self.assertRaises(ElementNotFoundError):
            ok.click()

    def test_focus_queries(self):
        self.assertTrue(self.form.control(class_name="TEdit", has_text=False).has_focus())
        self.assertFalse(self.form.control(title="OK").has_focus())
        self.assertEqual(self.aux.focused_control().handle, 4)
        self.assertEqual(self.aux.control_at(15, 15).handle, 2)

    def test_kind(self):
        self.assertEqual(self.form.control(title="OK").kind, "button")
        self.assertEqual(self.form.control(title="Nome").kind, "edit")


class WaitTests(unittest.TestCase):
    def test_wait_for_exists_succeeds_when_window_appears(self):
        aux, backend, _ = make_aux(timeout=2)
        w = aux.window(title="Nova")
        threading.Timer(0.1, lambda: backend.add(el(40, "Nova", "T"))).start()
        self.assertIs(w.wait_for_exists(timeout=2), w)
        self.assertEqual(w.handle, 40)

    def test_wait_for_exists_times_out(self):
        aux, _, _ = make_aux()
        t0 = time.monotonic()
        with self.assertRaises(AutomationTimeoutError):
            aux.window(title="Nunca").wait_for_exists(timeout=0.15)
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_zero_timeout_checks_once(self):
        aux, _, _ = make_aux()
        aux.window(title="Form1").wait_for_exists(timeout=0)
        with self.assertRaises(AutomationTimeoutError):
            aux.window(title="Nunca").wait_for_exists(timeout=0)

    def test_wait_for_gone(self):
        aux, backend, _ = make_aux(timeout=2)
        threading.Timer(0.1, lambda: backend.remove(11)).start()
        aux.window(title="Notepad").wait_for_gone(timeout=2)
        with self.assertRaises(AutomationTimeoutError):
            aux.window(title="Form1").wait_for_gone(timeout=0.1)

    def test_wait_for_enabled_and_focus_change(self):
        aux, backend, _ = make_aux(timeout=2)
        ctl = aux.window(title="Form1").control(title="Cancelar")
        threading.Timer(0.1, lambda: backend.add(el(3, "Cancelar", "TBitBtn", parent=1,
                                                    rect=(100, 10, 180, 40)))).start()
        ctl.wait_for_enabled(timeout=2)
        threading.Timer(0.1, lambda: setattr(backend, "fc", 7)).start()
        self.assertEqual(aux.wait_for_focus_change(timeout=2).handle, 7)
        with self.assertRaises(AutomationTimeoutError):
            aux.wait_for_focus_change(timeout=0.1)


if __name__ == "__main__":
    unittest.main()
