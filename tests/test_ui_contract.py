"""Verify every hard-coded UI element lookup exists in the shipped HTML."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "trainer" / "static"


class ElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "form":
            self.forms.append(attributes)


class UIContractTests(unittest.TestCase):
    def test_every_js_element_lookup_exists_in_html(self):
        html = (ROOT / "index.html").read_text("utf-8")
        js = (ROOT / "app.js").read_text("utf-8")
        parser = ElementParser()
        parser.feed(html)
        looked_up = set(re.findall(r'\bel\(["\']([\w-]+)["\']\)', js))
        missing = looked_up - set(parser.ids)
        self.assertFalse(missing, f"JavaScript references missing DOM IDs: {sorted(missing)}")
        self.assertEqual(len(parser.ids), len(set(parser.ids)), "Duplicate HTML IDs")
        self.assertIn("self-test", looked_up)
        self.assertIn("self-test-result", looked_up)

    def test_game_form_cannot_fallback_to_get_query(self):
        parser = ElementParser()
        parser.feed((ROOT / "index.html").read_text("utf-8"))
        form = next(x for x in parser.forms if x.get("id") == "game-form")
        self.assertEqual(form.get("method"), "post")


if __name__ == "__main__":
    unittest.main()
