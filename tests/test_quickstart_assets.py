"""Quick-start UI regression: checks assets and the existing read-only demo path.

These are static contract tests; they do not substitute for browser UX testing.
"""
from pathlib import Path
import unittest

WEB = Path(__file__).resolve().parents[1] / "ab_modbus" / "web"


class QuickStartAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.script = (WEB / "app.js").read_text(encoding="utf-8")
        cls.style = (WEB / "style.css").read_text(encoding="utf-8")

    def test_accessible_one_click_entry_and_results_anchor(self):
        self.assertIn('id="primera-prueba"', self.html)
        self.assertIn('aria-labelledby="quickstart-title"', self.html)
        self.assertIn('id="quick-demo"', self.html)
        self.assertIn('id="resultados"', self.html)
        self.assertIn('href="#resultados"', self.html)
        self.assertIn('data-quick-step="3"', self.html)

    def test_first_read_uses_existing_auth_read_only_demo(self):
        self.assertIn('$("demo").click()', self.script)
        self.assertIn('action("demo", async () => {', self.script)
        self.assertIn('await readOnce()', self.script)
        self.assertIn('api("/api/read"', self.script)
        self.assertIn('firstReadComplete = true;', self.script)
        self.assertIn('firstReadComplete = false;', self.script)
        self.assertNotIn('api("/api/write"', self.script)

    def test_responsive_and_focus_support(self):
        self.assertIn('.quickstart-steps', self.style)
        self.assertIn('@media(max-width:620px)', self.style)
        self.assertIn('button:focus-visible', self.style)


if __name__ == "__main__":
    unittest.main()
