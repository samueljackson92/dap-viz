"""Read a JET DAP key/value file into records."""

import re
from dataclasses import dataclass
from pathlib import Path

ENCODING = "latin-1"
CONTINUATION = "\\"


@dataclass(frozen=True)
class Record:
    """One key and its value. The value can have more than one line."""

    key: str
    value: str
    line: int


def parse_lines(lines: list[str]) -> list[Record]:
    """Make records from the lines of a DAP file.

    A line that ends with a backslash continues on the next line.
    """
    records: list[Record] = []
    key: str | None = None
    parts: list[str] = []
    start = 0
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        if key is None:
            key, _, text = line.partition(" ")
            parts = [text]
            start = number
        else:
            parts.append(line)
        if line.endswith(CONTINUATION):
            parts[-1] = parts[-1][: -len(CONTINUATION)]
            continue
        records.append(Record(key=key, value="\n".join(parts), line=start))
        key = None
    if key is not None:
        records.append(Record(key=key, value="\n".join(parts), line=start))
    return records


def read_dap(path: str | Path) -> list[Record]:
    """Read a DAP file and return its records."""
    with open(path, encoding=ENCODING) as handle:
        return parse_lines(handle.readlines())


def pulse_number(path: str | Path) -> int | None:
    """Get the pulse number from a file name such as DAP-0103169.txt."""
    match = re.search(r"(\d{4,})", Path(path).stem)
    return int(match.group(1)) if match else None
