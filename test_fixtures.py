"""Validate actual committed outputs, including the extraction boundary."""

from html.parser import HTMLParser
import hashlib
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
        if tag == "meta":
            assert (attrs.get("http-equiv") or "").strip().casefold() != "refresh", "Meta refresh"
        assert "style" not in attrs, "Inline style"
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
        if self.hidden == "style":
            assert "@import" not in data.casefold(), "CSS import"
        if self.hidden:
            self.blocks[self.hidden] += data
        else:
            self.visible.append(data)


class FixtureTests(unittest.TestCase):
    def test_real_outputs_reproduce_and_parse(self):
        expected_names = {"small.html", "20kb.html", "1mib.html", "4mib.html", "script-style.html", "joint-overflow.html"}
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

    def test_joint_overflow_has_eight_unchanged_paragraphs(self):
        from generate import PARAGRAPH

        data = (ROOT / "joint-overflow.html").read_text(encoding="ascii")
        self.assertEqual(data.count("<p>"), 8)
        self.assertEqual(data.count("</p>"), 8)
        self.assertEqual(data.count("<p>" + PARAGRAPH + "</p>"), 8)
        parser = ArticleParser()
        parser.feed(data)
        self.assertEqual(parser.blocks, {})
        self.assertEqual(parser.handlers, [])

    def test_original_five_bytes_unchanged(self):
        # Accepted merged baseline 7bb92ac948561dc85e8d907964598e5212b8a906.
        hashes = {
            "small.html": "069e0a9414ff7b0eb04368640f1b123b1b3ad62cf7c04eb992ab0b3cbb75ae45",
            "20kb.html": "842418d68d0efe96321f0fa77b2635ad86a226c1f8b69533e1e41f244bc3ce88",
            "1mib.html": "37050e939e40a37688f80a6e2dfefc4581c9dab6e801d6a42301023f4c5afc8e",
            "4mib.html": "022e9c41c87f956ce4649e5731737d429ee5fd2563f23a69948ae92c2bed6416",
            "script-style.html": "fdff428f0ea1c4223198f28030ed4fe55b348da7d2b739d3df62ce13d005f061",
        }
        for name, expected in hashes.items():
            with self.subTest(page=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_active_markup_is_rejected(self):
        cases = (
            '<meta http-equiv="refresh" content="0;url=https://example.invalid/">',
            '<meta HTTP-EQUIV="ReFrEsH" content="0">',
            '<p style="display:none">Hidden label</p>',
            '<style>@import "https://example.invalid/a.css";</style>',
            '<style>@IMPORT url(https://example.invalid/a.css);</style>',
        )
        for markup in cases:
            with self.subTest(markup=markup):
                with self.assertRaises(AssertionError):
                    ArticleParser().feed(markup)


if __name__ == "__main__":
    unittest.main()
