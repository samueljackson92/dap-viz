"""Make a pandas DataFrame from DAP records."""

import re

import numpy as np
import pandas as pd

from dap_viz.classify import (
    NUMBER_RE,
    STRING_CATEGORIES,
    Category,
    classify_value,
    is_categorical,
)
from dap_viz.parser import Record

INDEX_RE = re.compile(r"\d+")
FLAG_VALUES = {0.0, 1.0}


def split_key(key: str) -> tuple[str, str]:
    """Split a key into the system prefix and the name."""
    system, sep, name = key.partition("/")
    return (system, name) if sep else ("", key)


def family_of(key: str) -> tuple[str, tuple[int, ...]]:
    """Return the key family and the indices.

    The family is the key with each number in the name changed to '#'.
    The system prefix does not change.
    Example: 'Sc/NormCtrl.c3w12' gives ('Sc/NormCtrl.c#w#', (3, 12)).
    """
    system, name = split_key(key)
    indices = tuple(int(match) for match in INDEX_RE.findall(name))
    family_name = INDEX_RE.sub("#", name)
    return (f"{system}/{family_name}" if system else family_name), indices


def build_frame(records: list[Record]) -> pd.DataFrame:
    """Make one row for each record, with the category and the numeric value."""
    rows = []
    for record in records:
        system, name = split_key(record.key)
        family, indices = family_of(record.key)
        text = record.value.strip()
        rows.append(
            {
                "key": record.key,
                "system": system,
                "name": name,
                "family": family,
                "indices": indices,
                "n_indices": len(indices),
                "value": record.value,
                "category": str(classify_value(record.value)),
                "number": float(text) if NUMBER_RE.match(text) else np.nan,
                "lines": record.value.count("\n") + 1,
                "length": len(record.value),
                "line": record.line,
            }
        )
    frame = pd.DataFrame(rows)
    _refine_strings(frame)
    _add_numeric_kind(frame)
    return frame


def _refine_strings(frame: pd.DataFrame) -> None:
    """Change TEXT to CATEGORICAL for short labels from a small set."""
    mask = frame["category"].isin([str(c) for c in STRING_CATEGORIES])
    strings = frame.loc[mask]
    stripped = strings["value"].str.strip()
    value_counts = stripped.map(stripped.value_counts())
    family_size = strings.groupby("family")["key"].transform("size")
    family_distinct = stripped.groupby(strings["family"]).transform("nunique")
    categorical = [
        is_categorical(value, int(count), int(size), int(distinct))
        for value, count, size, distinct in zip(
            stripped, value_counts, family_size, family_distinct, strict=True
        )
    ]
    single_word = ~stripped.str.contains(r"\s", regex=True)
    frame.loc[mask, "category"] = np.select(
        [np.array(categorical), single_word.to_numpy()],
        [str(Category.CATEGORICAL), str(Category.IDENTIFIER)],
        default=str(Category.TEXT),
    )


def _add_numeric_kind(frame: pd.DataFrame) -> None:
    """Add the column numeric_kind: flag, integer or float."""
    numeric = frame["category"] == str(Category.NUMERIC)
    kinds = pd.Series("", index=frame.index, dtype=object)
    values = frame.loc[numeric, "number"]
    is_integer = frame.loc[numeric, "value"].str.strip().str.fullmatch(r"[+-]?\d+")
    kinds.loc[numeric] = np.where(is_integer, "integer", "float")
    family_is_flag = values.groupby(frame.loc[numeric, "family"]).transform(
        lambda group: len(group) > 1 and set(group.unique()) <= FLAG_VALUES
    )
    kinds.loc[family_is_flag[family_is_flag.astype(bool)].index] = "flag"
    frame["numeric_kind"] = kinds


def family_table(frame: pd.DataFrame, family: str) -> pd.DataFrame:
    """Return the rows of one family, sorted by the indices."""
    rows = frame[frame["family"] == family]
    return rows.sort_values("indices")
