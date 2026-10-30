"""Find the category of a DAP value and parse the structured values."""

import re
from dataclasses import dataclass, field
from enum import StrEnum


class Category(StrEnum):
    """The categories of DAP values."""

    NUMERIC = "numeric"
    NUMERIC_ARRAY = "numeric_array"
    EMPTY = "empty"
    ERROR = "error"
    FILEPATH = "filepath"
    WAVEFORM_REF = "waveform_ref"
    SIGNAL_PATH = "signal_path"
    DSL_WAVEFORM = "dsl_waveform"
    DSL_CONFIG = "dsl_config"
    DSL_TYPED_LIST = "dsl_typed_list"
    DSL_TIMER = "dsl_timer"
    DATETIME = "datetime"
    HEX = "hex"
    CATEGORICAL = "categorical"
    IDENTIFIER = "identifier"
    TEXT = "text"


CATEGORY_DESCRIPTIONS: dict[Category, str] = {
    Category.NUMERIC: "One integer or floating-point number",
    Category.NUMERIC_ARRAY: "Two or more numbers with spaces between them",
    Category.EMPTY: "No value",
    Category.ERROR: "Read error from the control system (starts with ****)",
    Category.FILEPATH: "Absolute path or configuration file name",
    Category.WAVEFORM_REF: "Reference to a stored waveform, DIR/name:version",
    Category.SIGNAL_PATH: "JPF-style signal path, sys/node/signal",
    Category.DSL_WAVEFORM: "Inline waveform definition: name target @ N t v ...",
    Category.DSL_CONFIG: "MARTe/GAM configuration block: Key = value { }",
    Category.DSL_TYPED_LIST: 'Typed list: R 1.0 I 0 C "text" ...',
    Category.DSL_TIMER: "Timer definition: npts=... I(n@dt) P(n@dt)",
    Category.DATETIME: "Date or time",
    Category.HEX: "Hexadecimal number",
    Category.CATEGORICAL: "Short label from a small set of values",
    Category.IDENTIFIER: "One-word name that is not repeated (tile, GAM, slot)",
    Category.TEXT: "Free text, names and comments",
}

# Thresholds for the second pass (categorical or text).
CATEGORICAL_MAX_LENGTH = 40
CATEGORICAL_MIN_REPEATS = 3
CATEGORICAL_MIN_FAMILY = 3

NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
NUMBER_RE = re.compile(rf"^{NUMBER}$")
HEX_RE = re.compile(r"^0[xX][0-9a-fA-F]+$")
DATE_RES = (
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),
    re.compile(r"^\w{3} \w{3} +\d{1,2} \d\d:\d\d:\d\d \d{4}$"),
    re.compile(r"^\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?$"),
    re.compile(r"^\d\d:\d\d:\d\d\b"),
)
FILE_NAME_RE = re.compile(
    r"^[\w.+-]+\.(?:cfg|txt|dat|xml|csv|ini|py|m|json|h5)$", re.IGNORECASE
)
WAVEFORM_REF_RE = re.compile(r"^[A-Za-z0-9_]+/[^\s/]+:\d+$")
SIGNAL_PATH_RE = re.compile(r"^[A-Za-z0-9_]+(?:/[\w.$+-]+){2,}$")
DSL_WAVEFORM_RE = re.compile(rf"^\S+\s+\S+\s+@\s+\d+(?:\s+{NUMBER})+")
TIMER_RE = re.compile(r"\bnpts=\d+")
TYPED_LIST_RE = re.compile(r'^(?:[A-Z] (?:"[^"]*"|\S+)\s*)+$')
CONFIG_RE = re.compile(r"^\s*[\w.+:-]+\s*=\s*", re.MULTILINE)

STRING_CATEGORIES = (Category.CATEGORICAL, Category.IDENTIFIER, Category.TEXT)


def classify_value(value: str) -> Category:
    """Return the category of one value. Use rules in order; the first match wins.

    This function returns TEXT for all plain strings. Use
    refine_strings() to find the CATEGORICAL values.
    """
    text = value.strip()
    if not text:
        return Category.EMPTY
    if text.startswith("****"):
        return Category.ERROR
    if NUMBER_RE.match(text):
        return Category.NUMERIC
    tokens = text.split()
    if len(tokens) > 1 and all(NUMBER_RE.match(token) for token in tokens):
        return Category.NUMERIC_ARRAY
    if HEX_RE.match(text):
        return Category.HEX
    if any(pattern.match(text) for pattern in DATE_RES):
        return Category.DATETIME
    if DSL_WAVEFORM_RE.match(text):
        return Category.DSL_WAVEFORM
    if TIMER_RE.search(text):
        return Category.DSL_TIMER
    if text.startswith("/") and "/" in text[1:] and "\n" not in text:
        return Category.FILEPATH
    if FILE_NAME_RE.match(text):
        return Category.FILEPATH
    if WAVEFORM_REF_RE.match(text):
        return Category.WAVEFORM_REF
    if SIGNAL_PATH_RE.match(text):
        return Category.SIGNAL_PATH
    if CONFIG_RE.match(text) and ("\n" in text or "{" in text):
        return Category.DSL_CONFIG
    if len(tokens) >= 4 and TYPED_LIST_RE.match(text):
        return Category.DSL_TYPED_LIST
    return Category.TEXT


def is_categorical(
    value: str, value_count: int, family_size: int, family_distinct: int
) -> bool:
    """Return True when a plain string is a label from a small set."""
    text = value.strip()
    if "\n" in text or len(text) > CATEGORICAL_MAX_LENGTH:
        return False
    if value_count >= CATEGORICAL_MIN_REPEATS:
        return True
    return family_size >= CATEGORICAL_MIN_FAMILY and family_distinct * 2 <= family_size


# --- Parsers for structured values -------------------------------------------


@dataclass
class Waveform:
    """An inline waveform definition."""

    name: str
    target: str
    times: list[float]
    values: list[float]
    comment: str = ""


def parse_dsl_waveform(value: str) -> Waveform | None:
    """Parse `name target @ N t0 v0 t1 v1 ... [comment]`. Return None on failure."""
    head, sep, tail = value.strip().partition("@")
    if not sep:
        return None
    head_tokens = head.split()
    tokens = tail.split()
    if not tokens or not tokens[0].isdigit():
        return None
    count = int(tokens[0])
    numbers = tokens[1 : 1 + 2 * count]
    if len(numbers) < 2 * count or not all(NUMBER_RE.match(t) for t in numbers):
        return None
    floats = [float(t) for t in numbers]
    return Waveform(
        name=head_tokens[0] if head_tokens else "",
        target=" ".join(head_tokens[1:]),
        times=floats[0::2],
        values=floats[1::2],
        comment=" ".join(tokens[1 + 2 * count :]),
    )


TIMER_SEGMENT_RE = re.compile(rf"([IP])\((\d+)@({NUMBER})\)")


@dataclass
class TimerSegment:
    """One segment of a timer: count samples with the interval dt (s)."""

    kind: str
    count: int
    dt: float


def parse_timer(value: str) -> tuple[str, int | None, list[TimerSegment]]:
    """Parse `CLOCK: npts=N I(n@dt) P(n@dt) ...`. Return clock, npts, segments."""
    clock = value.split(":", 1)[0].strip() if ":" in value else ""
    npts = re.search(r"npts=(\d+)", value)
    segments = [
        TimerSegment(kind, int(count), float(dt))
        for kind, count, dt in TIMER_SEGMENT_RE.findall(value)
    ]
    return clock, int(npts.group(1)) if npts else None, segments


def parse_numeric_array(value: str) -> list[float]:
    """Parse numbers that have spaces between them."""
    return [float(token) for token in value.split()]


@dataclass
class TypedItem:
    """One item of a typed list."""

    kind: str
    value: str | float


def parse_typed_list(value: str) -> list[TypedItem]:
    """Parse `R 1.0 I 0 C "text"`. R and I values become floats."""
    items: list[TypedItem] = []
    for kind, raw in re.findall(r'([A-Z]) ("[^"]*"|\S+)', value):
        if kind in "RI" and NUMBER_RE.match(raw):
            items.append(TypedItem(kind, float(raw)))
        else:
            items.append(TypedItem(kind, raw.strip('"')))
    return items


CONFIG_TOKEN_RE = re.compile(r'"[^"]*"|[{}=]|[^\s{}="]+')


@dataclass
class _Cursor:
    tokens: list[str]
    index: int = 0
    extra: list[str] = field(default_factory=list)

    def peek(self, offset: int = 0) -> str | None:
        position = self.index + offset
        return self.tokens[position] if position < len(self.tokens) else None

    def take(self) -> str:
        token = self.tokens[self.index]
        self.index += 1
        return token


ConfigValue = str | dict[str, "ConfigValue"]


def _parse_block(cursor: _Cursor) -> ConfigValue:
    """Parse tokens up to the closing brace or the end."""
    result: dict[str, ConfigValue] = {}
    words: list[str] = []
    while (token := cursor.peek()) is not None and token != "}":
        if cursor.peek(1) == "=":
            cursor.take()
            cursor.take()
            if cursor.peek() == "{":
                cursor.take()
                result[token] = _parse_block(cursor)
                if cursor.peek() == "}":
                    cursor.take()
            elif cursor.peek() is not None and cursor.peek() != "}":
                words_value: list[str] = [cursor.take().strip('"')]
                # A value can be more than one word before the next key.
                while (
                    (nxt := cursor.peek()) is not None
                    and nxt not in "{}"
                    and cursor.peek(1) != "="
                ):
                    words_value.append(cursor.take().strip('"'))
                result[token] = " ".join(words_value)
            else:
                result[token] = ""
        elif token == "{":
            cursor.take()
            words.append(str(_parse_block(cursor)))
            if cursor.peek() == "}":
                cursor.take()
        else:
            words.append(cursor.take().strip('"'))
    if not result:
        return " ".join(words)
    if words:
        result["_"] = " ".join(words)
    return result


def parse_config_block(value: str) -> ConfigValue:
    """Parse a MARTe/GAM configuration block into nested dictionaries."""
    cursor = _Cursor(CONFIG_TOKEN_RE.findall(value))
    result = _parse_block(cursor)
    return result


def flatten_config(config: ConfigValue, prefix: str = "") -> dict[str, str]:
    """Make a flat dictionary with dotted keys from a parsed block."""
    if not isinstance(config, dict):
        return {prefix or "value": config}
    flat: dict[str, str] = {}
    for key, item in config.items():
        name = f"{prefix}.{key}" if prefix else key
        flat.update(flatten_config(item, name))
    return flat
