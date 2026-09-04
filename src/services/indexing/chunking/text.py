import re

# Leading list markers used in hand-written resume descriptions.
_BULLET_RE = re.compile(r"^\s*(?:[-–—•*·>]+|\d+[.)])\s*")
_WHITESPACE_RE = re.compile(r"[ \t ]+")
_BLANK_LINES_RE = re.compile(r"\n{2,}")


def normalize_description(text: str) -> str:
    """Collapse the whitespace noise typical of pasted resume text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_LINES_RE.sub("\n", text)
    return text.strip()


def segments(text: str) -> list[str]:
    """Split a description into its smallest meaningful lines."""
    lines = []
    for raw_line in normalize_description(text=text).split("\n"):
        line = _BULLET_RE.sub("", raw_line).strip(" ;")
        if line:
            lines.append(line)
    return lines
