# Progress

## 2026-10-07 — web_processor cleanup pass

Goal: make `process_urls()` output cleaner and more LLM-friendly (no leftover
metadata/tags), and tighten the fetch path.

### Cleaning (`web_processor/cleaner.py`)

- Strip markdown escapes trafilatura emits (`\_`, `\[`, `\*`), `¶`, `†`/`‡`.
- Drop citation noise: `\[1\]`, `[1]`, `[*citation needed*]`, `[edit]`, and
  bibliography list items (`1. ↑ Author… Retrieved 2026-01-27`, `{{cite …}}`).
- Drop whole-line metadata: bylines (`By Jane Doe`), date stamps
  (`December 05, 2024 by The React Team`), `©`/copyright lines, link
  definitions, plus more chrome (menu/search/login/cart/back-to-top/…).
- Junk headings now match patterns too (`Notes and references`, `External links`).
- Titles drop the site-name suffix only when it matches the host
  (`Regular expression - Wikipedia` → `Regular expression`), so real
  subtitles survive.
- `_unwrap()` no longer joins source lines into prose; code-looking lines are
  kept apart (and separated by a blank line).

### Extraction (`web_processor/extractor.py`)

- `<pre>` blocks are replaced by placeholders before trafilatura and restored
  as fenced code afterwards. trafilatura flattens `<pre>` inside list items
  (every line joined with spaces) — this keeps line breaks and indentation.
  `<br/>` inside `<pre>` is converted to a newline first, otherwise the line
  breaks are lost.

### Pipeline / fetch (`web_processor/pipeline.py`, `fetcher.py`)

- One shared `httpx.AsyncClient` for a whole batch (connection pool instead of
  a client + TLS handshake per URL), capped at 8 concurrent requests.
- Streaming fetch with a 2 MB cap and a content-type check (skips PDFs/media).
- Exact-duplicate articles (same body or same title + lead) are dropped.

### Verified

- `python main.py` with a real query (searxng → research → clean article text).
- Wikipedia: footnote refs, `[*citation needed*]` and the reference list gone
  (~86% of extracted words kept; the removed part is citations/chrome).
- docs.python.org: 34 code blocks preserved with indentation (previously
  flattened where they sat inside list items).

### Lint

`ruff format` is clean. `ruff check web_processor` reports FURB167 / BLE001 /
PIE810 / RUF022 — the same rules already firing on the original code
(`re.I` style, broad `except`, unsorted `__all__`). Fixable with
`ruff check --fix web_processor`; the two `except Exception` are intentional.
