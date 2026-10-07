import re
from html import unescape

from lxml.html import fromstring as parse_fragment
from trafilatura import bare_extraction

from .models import Document, Section

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_HTML_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TITLE_TAG_RE = re.compile(r"</?[A-Za-z][^>\n]*>")
_PRE_RE = re.compile(r"<pre\b[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_CODE_PLACEHOLDER_RE = re.compile(r"@@code:(\d+)@@")

# Trafilatura flattens <pre> blocks that sit inside list items, joining every
# line with spaces. Replacing them with a placeholder keeps the line breaks;
# the real code is put back after extraction.
_MAX_CODE_CHARS = 20_000


def extract(html: str, url: str) -> Document | None:
    html, code_blocks = _hoist_pre_blocks(html)

    result = bare_extraction(
        html,
        url=url,
        favor_precision=True,
        include_comments=False,
        include_images=False,
        include_links=False,
        include_tables=True,
        # Markdown headings and fenced code, without HTML tags or link targets.
        include_formatting=True,
        deduplicate=True,
    )

    if not result:
        return None

    text = result.text
    if not text:
        return None

    text = _restore_code_blocks(text, code_blocks)

    sections, heading_title = parse_sections(text)
    if not sections:
        return None

    return Document(
        url=url,
        title=heading_title or _html_title(html),
        author=result.author,
        date=result.date,
        sections=sections,
    )


def _hoist_pre_blocks(html: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def replace(match: re.Match[str]) -> str:
        code = _pre_text(match.group(1))
        if not code.strip() or len(code) > _MAX_CODE_CHARS:
            return match.group(0)

        blocks.append(code.rstrip("\n"))
        return f"<p>@@code:{len(blocks) - 1}@@</p>"

    return _PRE_RE.sub(replace, html), blocks


def _pre_text(fragment: str) -> str:
    # <br/> is a line break in HTML; lxml.text_content() would drop it.
    fragment = _BR_RE.sub("\n", fragment)

    try:
        return parse_fragment(f"<div>{fragment}</div>").text_content()
    except Exception:
        return unescape(_TAG_RE.sub("", fragment))


def _restore_code_blocks(text: str, blocks: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index >= len(blocks):
            return ""

        code = blocks[index].strip("\n")
        if not code.strip():
            return ""
        return f"\n```\n{code}\n```\n"

    return _CODE_PLACEHOLDER_RE.sub(replace, text)


def parse_sections(text: str) -> tuple[list[Section], str | None]:
    """Split markdown-ish article text into sections.

    The first H1 becomes the document title. Hash marks inside fenced code
    stay in the code block.
    """
    sections: list[Section] = []
    h1_title: str | None = None
    current_heading: str | None = None
    current_content: list[str] = []
    in_fence = False

    def has_content(lines: list[str]) -> bool:
        return any(line.strip() for line in lines)

    def flush() -> None:
        nonlocal current_heading, current_content
        if has_content(current_content):
            while current_content and not current_content[0].strip():
                current_content.pop(0)
            while current_content and not current_content[-1].strip():
                current_content.pop()
            sections.append(
                Section(
                    heading=current_heading,
                    content="\n".join(current_content).strip(),
                )
            )
        current_heading = None
        current_content = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            current_content.append(stripped)
            continue

        if in_fence:
            current_content.append(line.rstrip())
            continue

        match = _HEADING_RE.match(stripped)
        if match and len(match.group(2)) <= 180:
            level = len(match.group(1))
            heading_text = match.group(2).strip()

            if level == 1 and h1_title is None:
                if has_content(current_content):
                    flush()
                h1_title = heading_text
                current_heading = None
                continue

            flush()
            current_heading = heading_text
            continue

        current_content.append(line.rstrip())

    flush()
    return sections, h1_title


def _html_title(html: str) -> str | None:
    match = _HTML_TITLE_RE.search(html)
    if not match:
        return None

    title = unescape(match.group(1))
    title = _TITLE_TAG_RE.sub("", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title or None
