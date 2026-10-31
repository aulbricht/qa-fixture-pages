# qa-fixture-pages
Synthetic test pages for automated QA. No real content.

These six ASCII-only pages support SNO-685 extraction checks on PR5085
`aaf3cd0b3ec0b841227640c0d3fcccf517fd9a19`. All observations describe an
invented archive; the arithmetic is deliberately checkable.

Generate with Python 3 (standard library only):

```sh
python3 generate.py
python3 generate.py --check
python3 -m unittest -v test_fixtures.py
```

| File | Size / purpose |
| --- | --- |
| `small.html` | 1,536 bytes; short article |
| `20kb.html` | Exactly 20,480 bytes of article body, plus HTML wrapper |
| `1mib.html` | Exactly 1,048,576 bytes total |
| `4mib.html` | Exactly 4,194,304 bytes total |
| `script-style.html` | Short article plus over 100 KB each of script and style data |
| `joint-overflow.html` | 2,956 bytes; exactly eight repeats of the existing synthetic paragraph |

The joint-overflow page supports QA row #12d. Its measured size is 2,956 UTF-8
bytes, rather than the earlier 3,071-byte estimate; no padding or cropping is
used. The source size does not prove individual proof-frame admission or joint
serialized overflow. QA must measure those in the consuming application and
check that ordinary source checking remains intact. The original five page
hashes are locked by a regression test.

The script block uses the inert `application/json` type. CSS and event handlers
contain only comments. Every page also denies scripts, styles and external
resources through a meta Content Security Policy. The `SCRIPT_ONLY_SENTINEL`,
`STYLE_ONLY_SENTINEL` and `HANDLER_ONLY_SENTINEL` markers must not appear in
extracted article text; the visible sentence about surviving extraction must
remain. There are no external resources, trackers or network calls.

GitHub Pages publishes from `main` at `/`. Draft PR contents are not served until
the PM merges. Public URLs use `https://aulbricht.github.io/qa-fixture-pages/`
followed by the filename. Verify served bytes against the committed SHA-256
after publication; passing generator checks alone does not prove publication or
the consuming application's extraction behavior.

Static Pages cannot cover redirects, deliberately slow responses, or custom HTTP
status codes. Those QA rows remain unsupported by these fixtures.
