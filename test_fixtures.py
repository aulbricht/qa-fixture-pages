"""Validate actual committed outputs, including the extraction boundary."""

from html.parser import HTMLParser
import unittest

from generate import ROOT, fixtures


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = None
        self.visible = []
        self.blocks = {}
        self.handlers = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.hidden = tag
            self.blocks[tag] = ""
        if tag == "script":
            assert attrs.get("type") == "application/json", "Executable script"
        assert tag not in ("iframe", "object", "embed", "link", "img", "base")
        assert not {"src", "href", "action", "srcset"}.intersection(attrs)
        for key, value in attrs.items():
            if key.startswith("on"):
                self.handlers.append(value)
                assert value == "/* HANDLER_ONLY_SENTINEL */"

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None

    def handle_data(self, data):
        if self.hidden:
            self.blocks[self.hidden] += data
        else:
            self.visible.append(data)


class FixtureTests(unittest.TestCase):
    def test_real_outputs_reproduce_and_parse(self):
        expected_names = {"small.html", "20kb.html", "1mib.html", "4mib.html", "script-style.html"}
        self.assertEqual(set(fixtures()), expected_names)
        for name, generated in fixtures().items():
            with self.subTest(page=name):
                actual = (ROOT / name).read_bytes()
                self.assertEqual(actual, generated)
                self.assertEqual(actual, fixtures()[name])
                parser = ArticleParser()
                parser.feed(actual.decode("ascii"))
                text = "".join(parser.visible)
                self.assertIn("SYNTHETIC QA FIXTURE, SNO-685", text)
                self.assertIn("twelve blue boxes and eight green boxes", text)
                self.assertIn("twenty boxes", text)
                for sentinel in ("SCRIPT_ONLY_SENTINEL", "STYLE_ONLY_SENTINEL", "HANDLER_ONLY_SENTINEL"):
                    self.assertNotIn(sentinel, text)
                self.assertIn(b"default-src 'none'; script-src 'none'", actual)
                if name == "script-style.html":
                    self.assertGreater(len(parser.blocks["script"]), 100_000)
                    self.assertGreater(len(parser.blocks["style"]), 100_000)
                    self.assertEqual(len(parser.handlers), 2)
                    self.assertIn("This visible sentence should survive extraction.", text)
                else:
                    self.assertEqual(parser.blocks, {})
                    self.assertEqual(parser.handlers, [])

    def test_sizes(self):
        sizes = {name: len((ROOT / name).read_bytes()) for name in fixtures()}
        self.assertTrue(1024 <= sizes["small.html"] <= 2048)
        self.assertEqual(sizes["1mib.html"], 1_048_576)
        self.assertEqual(sizes["4mib.html"], 4_194_304)
        body = (ROOT / "20kb.html").read_bytes().split(b"</h1>\n", 1)[1].split(b"</article>", 1)[0]
        self.assertEqual(len(body), 20_480)


if __name__ == "__main__":
    unittest.main()
