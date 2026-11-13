import unittest

from auxiliar_interface import Criteria, InvalidCriteriaError, Rect
from tests.fakes import el


class CriteriaTests(unittest.TestCase):
    def setUp(self):
        self.ok = el(2, "&OK", "TBitBtn", parent=1, rect=(10, 10, 90, 40))
        self.blank = el(4, "", "TEdit", parent=1, rect=(10, 60, 200, 90), enabled=False)

    def test_title_exact_ignores_accelerator(self):
        self.assertTrue(Criteria(title="&OK").matches(self.ok))
        self.assertTrue(Criteria(title="OK").matches(self.ok))
        self.assertFalse(Criteria(title="Cancel").matches(self.ok))

    def test_contains_regex_and_case(self):
        self.assertTrue(Criteria(title_contains="O").matches(self.ok))
        self.assertTrue(Criteria(title_re=r".*OK").matches(self.ok))
        self.assertFalse(Criteria(title_re=r"OK").matches(self.ok))  # re.match ancorado no início
        self.assertTrue(Criteria(title="ok", ignore_case=True).matches(self.ok))

    def test_class_single_multiple_and_regex(self):
        self.assertTrue(Criteria(class_name="TBitBtn").matches(self.ok))
        self.assertTrue(Criteria(class_name=["TEdit", "TBitBtn"]).matches(self.ok))
        self.assertTrue(Criteria(class_name_re="T.*Btn").matches(self.ok))
        self.assertFalse(Criteria(class_name="Button").matches(self.ok))

    def test_state_filters(self):
        self.assertTrue(Criteria(has_text=False).matches(self.blank))
        self.assertTrue(Criteria(enabled=False).matches(self.blank))
        self.assertFalse(Criteria(visible=False).matches(self.ok))

    def test_position_filters(self):
        self.assertTrue(Criteria(inside=Rect(0, 0, 100, 100)).matches(self.ok))
        self.assertFalse(Criteria(inside=Rect(500, 500, 600, 600)).matches(self.ok))
        self.assertTrue(Criteria(at_point=(20, 20)).matches(self.ok))

    def test_index_and_predicate(self):
        items = [el(i, "x", "T") for i in range(1, 5)]
        self.assertEqual([i.handle for i in Criteria(index=2).select(items)], [3])
        self.assertEqual(Criteria(index=9).select(items), [])
        self.assertEqual(len(Criteria(predicate=lambda i: i.handle % 2 == 0).select(items)), 2)

    def test_combine(self):
        both = Criteria(class_name="TBitBtn") & Criteria(title="OK", visible=True)
        self.assertTrue(both.matches(self.ok))
        with self.assertRaises(InvalidCriteriaError):
            Criteria(title="A") & Criteria(title="B")

    def test_invalid_regex_and_index(self):
        with self.assertRaises(InvalidCriteriaError):
            Criteria(title_re="(")
        with self.assertRaises(InvalidCriteriaError):
            Criteria(index=-1)

    def test_describe(self):
        self.assertIn("title='OK'", Criteria(title="OK").describe())
        self.assertEqual(Criteria().describe(), "(sem critérios)")


if __name__ == "__main__":
    unittest.main()
