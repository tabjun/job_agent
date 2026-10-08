from html.parser import HTMLParser
import unittest

from job_agent.ui.page import remote_page
from job_agent.ui.server import STATIC


class Options(HTMLParser):
    def __init__(self):
        super().__init__()
        self.select = None
        self.values = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self.select = attrs.get("id")
        elif tag == "option":
            self.values.setdefault(self.select, []).append(attrs.get("value"))

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None


class RemotePageTests(unittest.TestCase):
    def test_default_and_explicit_model_policy_applies_before_javascript(self):
        source = (STATIC / "index.html").read_text(encoding="utf-8")
        for providers in [("none",), ("none", "custom"), ("none", "openai", "gemini")]:
            page = remote_page(source, providers).decode()
            parsed = Options()
            parsed.feed(page)
            self.assertEqual(parsed.values["provider"], ["none"])
            self.assertEqual(parsed.values["source"], ["manual"])
            self.assertNotIn("과금", page)
            self.assertIn('id="ai-consent"', page)
        self.assertNotIn("과금", source)

    def test_other_selects_and_entities_are_preserved(self):
        source = '<!doctype html><select id="provider"><option value="openai">Hide</option><option value="none">A &amp; B</option></select><select id="other"><option value="openai">Keep &#65;</option></select>'
        page = remote_page(source, ["none"]).decode()
        self.assertNotIn("Hide", page)
        self.assertIn("A &amp; B", page)
        self.assertIn("Keep &#65;", page)
