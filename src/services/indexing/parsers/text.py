import re
from html import unescape

# Tags that end a line of a description, so the chunker still sees lines.
_BREAK_RE = re.compile(r"</?(?:br|p|div|li|tr|h[1-6])[^>]*>", flags=re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_LINES_RE = re.compile(r"\n{2,}")


def to_plain_text(value: str | None) -> str:
    """Return HTML written in a resume as the plain text it reads as."""
    if not value:
        return ""

    text = _BREAK_RE.sub("\n", value)
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES_RE.sub("\n", text).strip()
