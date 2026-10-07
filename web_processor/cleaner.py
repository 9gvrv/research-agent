import re
from html import unescape
from urllib.parse import urlparse

from .models import Document, Section

# Tags that show up when a page's markup leaks into the article text.
_TAG_RE = re.compile(r"</?[A-Za-z][^>\n]*>")
_SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_CITE_WORD_RE = re.compile(
    r"\[\s*\*?\s*(?:update|citation needed|dead link|better source needed"
    r"|edit|nb \d+|note \d+)\s*\*?\s*\]",
    re.I,
)
_CITE_NUM_RE = re.compile(r"\[\d{1,3}(?:\s*[,–-]\s*\d{1,3})*\]")
_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Markdown escapes trafilatura emits so literal `*`, `_`, `[` stay text.
_MD_ESCAPE_RE = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~])")
_PILCROW_RE = re.compile(r"¶")
_DAGGER_RE = re.compile(r"[†‡]")
_LINK_DEF_RE = re.compile(r"^\[[^\]]+\]:\s*\S+")

# A list item that is really a footnote/bibliography entry, not prose.
_CITE_LINE_RE = re.compile(
    r"^(?:"
    r"\d{1,3}\.\s+.*(?:"
    r"↑|{{cite|{{harv|\bdoi:|\bisbn\b|\bissn\b|\bs2cid\b|\bpmid\b"
    r"|retrieved\s+(?:\w+\s+\d{1,2},?\s+)?\d{4}"
    r"|archived from the original"
    r"|\(\d{1,2}\s+\w+\s+\d{4}\)"
    r")"
    r"|↑.*"
    r")",
    re.I,
)

_BYLINE_RE = re.compile(
    r"^(?:[Bb]y|[Ww]ritten by|[Pp]osted by|[Aa]uthored by)"
    r"\s+[A-Z][\w.'\u2019-]+(?:\s+[A-Z][\w.'\u2019-]+){0,4}"
    r"(?:,\s*[^,]+)?$"
)
_DATE_STAMP_RE = re.compile(
    r"^(?:(?:last\s+)?(?:updated|modified|edited|published|posted)(?:\s+on)?\s*:?\s*)?"
    r"(?:\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})"
    r"\.?(?:\s+by\s+.*)?$",
    re.I,
)
_COPYRIGHT_RE = re.compile(r"^(?:©|\(c\)|copyright)[\s©]*(?:\d{4}|©).{0,80}$", re.I)

# "Article | Site Name", "Article — Site Name", "Article - Site Name".
_TITLE_SEP_RE = re.compile(r"\s+(?:[|–—]|-)\s+")
_GENERIC_TLDS = {"com", "org", "net", "co", "gov", "edu", "mil"}

# Whole-line chrome. Real sentences that merely mention these words stay.
_BOILERPLATE_RE = re.compile(
    r"^(?:"
    r"share(?: this(?: article| post| story)?)?(?: on \w+)?"
    r"|follow us(?: on \w+)?"
    r"|subscribe(?: to (?:our )?newsletter)?(?: now)?"
    r"|sign up(?: for(?: our)? newsletter)?"
    r"|sign in|log ?in|my account|create an account"
    r"|newsletter"
    r"|advertisement"
    r"|sponsored(?: content)?"
    r"|related (?:articles|posts|stories)"
    r"|you (?:may|might) also like"
    r"|read more|read next|continue reading|show (?:more|all|less)"
    r"|skip to (?:content|main(?: content)?|navigation|search)"
    r"|table of contents"
    r"|contents"
    r"|all rights reserved\.?"
    r"|cookies?"
    r"|cookie (?:policy|settings|preferences)"
    r"|we use cookies\.?"
    r"|accept (?:all )?cookies"
    r"|privacy policy"
    r"|terms of (?:use|service)"
    r"|tags?\s*:.*"
    r"|keywords?\s*:.*"
    r"|categor(?:y|ies)\s*:.*"
    r"|filed under\b.*"
    r"|posted in\b.*"
    r"|this article is part of a series\b.*"
    r"|enable javascript.*"
    r"|javascript (?:is )?(?:required|disabled).*"
    r"|[0-9]+ min(?:ute)? read"
    r"|comments?"
    r"|\d+ comments?"
    r"|post a comment|leave a comment|reply"
    r"|back to top"
    r"|home page|homepage|sitemap|rss"
    r"|menu|search|home|about us|contact us"
    r"|advertise(?: with us)?|write for us"
    r"|cart|checkout"
    r"|dark mode|light mode"
    r"|toggle (?:menu|navigation|theme)"
    r"|download the app|get the app"
    r"|watch(?: the)? video|listen now"
    r"|next(?: page)?|previous page"
    r"|tweet this|email this|print this|copy link"
    r")$",
    re.I,
)
_URL_ONLY_RE = re.compile(r"https?://\S+", re.I)
_RULE_RE = re.compile(r"[\s|:\-–—*•·.^↑↓_]+")
_LIST_ITEM_RE = re.compile(r"([-*+]|[0-9]{1,3}[.)])\s")
_LOW_VALUE_SECTION_RE = re.compile(
    r"part of a series|cookie policy|subscribe to our newsletter",
    re.I,
)
_ERROR_BODY_RE = re.compile(
    r"page (?:you(?:'| a)re looking for )?(?:doesn'?t exist|does not exist|has been moved|could not be found)|has slithered away",
    re.I,
)

_JUNK_HEADINGS = {
    "reference",
    "references",
    "external link",
    "external links",
    "see also",
    "further reading",
    "bibliography",
    "footnote",
    "footnotes",
    "navigation",
    "comment",
    "comments",
    "share",
    "tag",
    "tags",
    "category",
    "categories",
    "sitemap",
    "site map",
    "table of contents",
    "contents",
}
_JUNK_HEADING_RE = re.compile(
    r"^(?:notes?\s+(?:and|&)\s+(?:references?|sources?)"
    r"|references?(?:\s+(?:and|&)\s+notes?)?"
    r"|footnotes?|bibliography|works cited|external links?)[.:]?$",
    re.I,
)
_GENERIC_AUTHORS = {
    "admin",
    "staff",
    "editor",
    "anonymous",
    "unknown",
    "none",
    "n/a",
    "null",
}

_CODE_TOKEN = "\ue000C{}\ue001"


def clean_document(document: Document) -> Document | None:
    document.title = clean_title(document.title, document.url)
    document.author = _clean_person(document.author)
    document.date = _clean_date(document.date)

    cleaned: list[Section] = []
    seen: set[tuple[str, str]] = set()

    for section in document.sections:
        heading = clean_heading(section.heading)
        content = clean_text(section.content)

        if not content:
            continue

        if document.title and heading and _same(heading, document.title):
            heading = None

        if heading and (
            heading.casefold() in _JUNK_HEADINGS or _JUNK_HEADING_RE.match(heading)
        ):
            continue

        if len(content) < 500 and _LOW_VALUE_SECTION_RE.search(content):
            continue

        if document.title and heading is None:
            content = _strip_repeated_title(content, document.title)
            if not content:
                continue

        key = ((heading or "").casefold(), content)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(Section(heading=heading, content=content))

    if _is_error_page(document.title, cleaned):
        return None

    if not cleaned:
        return None

    document.sections = cleaned
    return document


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    text = _INVISIBLE_RE.sub("", text)
    text = _CONTROL_RE.sub("", text)

    pieces: list[str] = []
    for kind, chunk in _split_fences(text):
        if kind == "code":
            chunk = unescape(chunk).strip("\n")
            if chunk:
                pieces.append(chunk)
            continue

        prose = _clean_prose(chunk)
        if prose:
            pieces.append(prose)

    return "\n\n".join(pieces).strip()


def clean_heading(heading: str | None) -> str | None:
    if not heading:
        return None

    heading = unescape(heading)
    heading = _COMMENT_RE.sub("", heading)
    heading = _TAG_RE.sub("", heading)
    heading = heading.replace("¶", "")
    heading = re.sub(r"\s+", " ", heading).strip(" \t|*_")
    return heading or None


def clean_title(title: str | None, url: str | None = None) -> str | None:
    title = clean_heading(title)
    if not title:
        return None

    # "<article> | Site Name" and "<article> — Site Name" are page-title chrome.
    # Only the part that names the site itself goes; the source URL already
    # says where the document came from.
    label = _site_label(url)
    if label:
        separators = list(_TITLE_SEP_RE.finditer(title))
        if separators:
            tail = title[separators[-1].end() :].strip()
            if tail and len(tail) <= 60 and label in _label_key(tail):
                title = title[: separators[-1].start()].strip()

    return title or None


def _site_label(url: str | None) -> str | None:
    if not url:
        return None

    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None

    parts = [part for part in host.lower().removeprefix("www.").split(".") if part]
    if len(parts) < 2:
        return None

    label = parts[-2]
    if label in _GENERIC_TLDS and len(parts) >= 3:
        label = parts[-3]
    return label or None


def _label_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _clean_prose(text: str) -> str:
    placeholders: list[str] = []

    def hold(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return _CODE_TOKEN.format(len(placeholders) - 1)

    text = _INLINE_CODE_RE.sub(hold, text)
    text = _SCRIPT_RE.sub(" ", text)
    text = _COMMENT_RE.sub(" ", text)
    text = unescape(text)
    text = _TAG_RE.sub("", text)
    text = _MD_ESCAPE_RE.sub(r"\1", text)
    text = _CITE_WORD_RE.sub(" ", text)
    text = _CITE_NUM_RE.sub("", text)
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _PILCROW_RE.sub("", text)
    text = _DAGGER_RE.sub(" ", text)

    lines: list[str] = []
    for line in text.splitlines():
        normalized = _normalize_line(line)
        if normalized is None:
            continue
        if normalized == "":
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if lines and lines[-1] == normalized:
            continue
        lines.append(normalized)

    lines = _drop_leading_nav_table(lines)
    lines = _unwrap(lines)
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if placeholders:
        cleaned = re.sub(
            r"\ue000C(\d+)\ue001",
            lambda match: placeholders[int(match.group(1))],
            cleaned,
        )
    return cleaned


def _normalize_line(line: str) -> str | None:
    if not line.strip():
        return ""

    indent_match = re.match(r"[ \t]+", line)
    indent = ""
    body = line.strip()
    if indent_match:
        indent = indent_match.group(0).replace("\t", "  ")[:8]

    body = re.sub(r"[ \t]{2,}", " ", body)
    body = re.sub(r"\s+([,.;:!?])", r"\1", body)
    body = re.sub(r"\[\s*\]", "", body)
    body = re.sub(r"\(\s*\)", "", body)
    body = re.sub(r"[ \t]{2,}", " ", body).strip()

    if not body or _is_noise_line(body):
        return None

    if indent and _LIST_ITEM_RE.match(body):
        return f"{indent}{body}"
    return body


def _is_noise_line(body: str) -> bool:
    if _BOILERPLATE_RE.match(body):
        return True
    if _URL_ONLY_RE.fullmatch(body):
        return True
    if _RULE_RE.fullmatch(body):
        return True
    if _LINK_DEF_RE.match(body):
        return True
    if _CITE_LINE_RE.match(body):
        return True
    if _BYLINE_RE.match(body):
        return True
    if _DATE_STAMP_RE.match(body):
        return True
    if _COPYRIGHT_RE.match(body):
        return True

    if "|" in body:
        cells = [cell.strip() for cell in body.strip("|").split("|")]
        cells = [cell for cell in cells if cell and not re.fullmatch(r"[\-:\s]+", cell)]
        if not cells:
            return True
        if all(_BOILERPLATE_RE.match(cell) for cell in cells):
            return True

    return False


def _drop_leading_nav_table(lines: list[str]) -> list[str]:
    """Drop a leading markdown table that is only a site nav box."""
    start = 0
    while start < len(lines) and lines[start] == "":
        start += 1

    end = start
    while end < len(lines) and (
        lines[end] == "" or lines[end].lstrip().startswith("|")
    ):
        end += 1

    block = "\n".join(lines[start:end])
    if "part of a series" not in block.casefold():
        return lines

    return lines[end:]


def _unwrap(lines: list[str]) -> list[str]:
    """Join hard-wrapped prose lines. List items, tables, and code stay put."""
    out: list[str] = []
    buf: str | None = None

    for line in lines:
        if line == "":
            if buf is not None:
                out.append(buf)
                buf = None
            if out and out[-1] != "":
                out.append("")
            continue

        if buf is None:
            buf = line
            continue

        if (
            len(buf) >= 60
            and not _ends_block(buf)
            and not _is_block_start(buf)
            and not _is_block_start(line)
            and not _looks_like_code(buf)
            and not _looks_like_code(line)
        ):
            buf = f"{buf} {line.lstrip()}"
            continue

        out.append(buf)
        if _looks_like_code(buf) != _looks_like_code(line):
            out.append("")
        buf = line

    if buf is not None:
        out.append(buf)
    return out


def _ends_block(line: str) -> bool:
    return line.rstrip().endswith((".", "!", "?", ":", ";", "。", "…"))


def _is_block_start(line: str) -> bool:
    stripped = line.lstrip()
    return bool(re.match(r"(```|\||>|#|[-*+]\s|\d{1,3}[.)]\s)", stripped))


_CODE_LINE_RE = re.compile(
    r"^(?:"
    r"(?:>>>|\.\.\.)\s+"
    r"|(?:import|from|def|class|async|await|return|try|except|finally|raise)\b"
    r"|for\s+\w+\s+in\b"
    r"|while\s+\w+\s*[:=(]"
    r"|print\("
    r"|\w+\s*=\s*\S"
    r"|\w+\.\w+\("
    r"|\w+\([^)]*\)\s*$"
    r")"
)


def _looks_like_code(line: str) -> bool:
    """True for source lines that must not be joined into prose."""
    return bool(_CODE_LINE_RE.match(line.lstrip()))


def _split_fences(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    buf: list[str] = []
    in_code = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            marker = line.strip()
            if not in_code:
                if buf:
                    parts.append(("prose", "\n".join(buf)))
                    buf = []
                buf = [marker]
                in_code = True
            else:
                buf.append(marker)
                parts.append(("code", "\n".join(buf)))
                buf = []
                in_code = False
            continue
        buf.append(line.rstrip() if in_code else line)

    if buf:
        parts.append(("code" if in_code else "prose", "\n".join(buf)))
    return parts


def _strip_repeated_title(content: str, title: str) -> str:
    lines = content.splitlines()
    if lines and _same(lines[0].lstrip("#").strip(), title):
        return "\n".join(lines[1:]).strip()
    return content


def _clean_person(value: str | None) -> str | None:
    value = clean_heading(value)
    if not value or len(value) > 80:
        return None
    if value.casefold() in _GENERIC_AUTHORS:
        return None
    if re.search(r"https?://|www\.|@", value):
        return None
    if _BOILERPLATE_RE.match(value):
        return None
    return value


def _clean_date(value: str | None) -> str | None:
    value = clean_heading(value)
    if not value:
        return None
    if re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", value):
        return value
    return None


def _is_error_page(title: str | None, sections: list[Section]) -> bool:
    title_norm = (title or "").strip().casefold()
    if title_norm in {"403", "404", "500", "not found", "page not found"}:
        return True
    if title_norm.startswith("404") or title_norm.startswith("not found"):
        return True

    body = "\n".join(section.content for section in sections)
    return len(body) < 400 and bool(_ERROR_BODY_RE.search(body))


def _same(left: str, right: str) -> bool:
    return (
        re.sub(r"\s+", " ", left).strip().casefold()
        == re.sub(r"\s+", " ", right).strip().casefold()
    )
