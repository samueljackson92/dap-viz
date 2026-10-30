"""Figures for each value category."""

import pandas as pd
import plotly.graph_objects as go

from dap_viz.classify import (
    Waveform,
    parse_dsl_waveform,
    parse_numeric_array,
    parse_timer,
)
from dap_viz.views.common import (
    HIGHLIGHT,
    PRIMARY,
    SEQUENTIAL,
    SERIES,
    empty_figure,
)

MAX_HEATMAP_ROWS = 200
MAX_PATH_NODES = 4000


def varying_positions(indices: pd.Series) -> list[int]:
    """Return the index positions that change inside a family."""
    if indices.empty:
        return []
    width = len(indices.iloc[0])
    return [p for p in range(width) if len({ix[p] for ix in indices}) > 1]


def family_figure(frame: pd.DataFrame, family: str, highlight: str | None = None):
    """Plot the numeric values of one key family.

    One changing index gives a bar chart. Two or more give a heatmap.
    """
    rows = frame[(frame["family"] == family) & frame["number"].notna()]
    if rows.empty:
        return empty_figure(f"No numeric values in {family}")
    rows = rows.sort_values("indices")
    positions = varying_positions(rows["indices"])
    title = f"{family}  ({len(rows)} numeric keys)"
    if len(positions) <= 1:
        x = (
            [ix[positions[0]] for ix in rows["indices"]]
            if positions
            else list(rows["key"])
        )
        colors = [HIGHLIGHT if key == highlight else PRIMARY for key in rows["key"]]
        figure = go.Figure(
            go.Bar(
                x=x,
                y=rows["number"],
                marker={"color": colors, "cornerradius": 4},
                customdata=rows["key"],
                hovertemplate="%{customdata}<br>value = %{y}<extra></extra>",
            )
        )
        figure.update_layout(title=title, xaxis_title="index", yaxis_title="value")
        return figure
    column = positions[-1]
    row_positions = positions[:-1]
    rows = rows.assign(
        col=[ix[column] for ix in rows["indices"]],
        row=[".".join(str(ix[p]) for p in row_positions) for ix in rows["indices"]],
    )
    grid = rows.pivot_table(
        index="row", columns="col", values="number", aggfunc="first"
    )
    keys = rows.pivot_table(index="row", columns="col", values="key", aggfunc="first")
    grid = grid.iloc[:MAX_HEATMAP_ROWS]
    keys = keys.reindex_like(grid)
    figure = go.Figure(
        go.Heatmap(
            z=grid.values,
            x=[str(c) for c in grid.columns],
            y=[str(r) for r in grid.index],
            customdata=keys.values,
            colorscale=SEQUENTIAL,
            xgap=2,
            ygap=2,
            hovertemplate="%{customdata}<br>value = %{z}<extra></extra>",
        )
    )
    if highlight in set(rows["key"]):
        hit = rows[rows["key"] == highlight].iloc[0]
        figure.add_trace(
            go.Scatter(
                x=[str(hit["col"])],
                y=[str(hit["row"])],
                mode="markers",
                marker={"symbol": "square-open", "size": 16, "color": HIGHLIGHT},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title=f"index {column + 1}",
        yaxis_title=" / ".join(f"index {p + 1}" for p in row_positions),
        xaxis={"type": "category"},
        yaxis={"type": "category", "autorange": "reversed"},
    )
    return figure


def waveforms_figure(
    items: list[tuple[str, Waveform]], normalise: bool = False
) -> go.Figure:
    """Plot one or more inline waveforms against time on one axis."""
    if not items:
        return empty_figure("Select one or more waveforms")
    figure = go.Figure()
    for slot, (key, wave) in enumerate(items[: len(SERIES)]):
        values = wave.values
        if normalise:
            peak = max((abs(v) for v in values), default=0.0) or 1.0
            values = [v / peak for v in values]
        figure.add_trace(
            go.Scatter(
                x=wave.times,
                y=values,
                name=key,
                mode="lines+markers",
                line={"width": 2, "color": SERIES[slot]},
                marker={"size": 8},
                hovertemplate=f"{key}<br>t = %{{x}}<br>v = %{{y}}<extra></extra>",
            )
        )
    figure.update_layout(
        xaxis_title="time (s)",
        yaxis_title="value / peak" if normalise else "value",
        hovermode="x unified",
        showlegend=True,
    )
    return figure


def waveform_figure(key: str, value: str) -> go.Figure:
    """Plot one inline waveform."""
    wave = parse_dsl_waveform(value)
    if wave is None:
        return empty_figure("Cannot parse this waveform")
    figure = waveforms_figure([(key, wave)])
    figure.update_layout(
        title=f"{wave.name}  →  {wave.target}  ({len(wave.times)} points)",
        showlegend=False,
    )
    return figure


def timer_figure(value: str) -> go.Figure:
    """Plot the sample interval of a timer against the time."""
    clock, npts, segments = parse_timer(value)
    if not segments:
        return empty_figure("No timer segments")
    times: list[float] = []
    intervals: list[float] = []
    labels: list[str] = []
    elapsed = 0.0
    for segment in segments:
        duration = segment.count * segment.dt
        times += [elapsed, elapsed + duration]
        intervals += [segment.dt, segment.dt]
        labels += [f"{segment.kind}({segment.count}@{segment.dt:g})"] * 2
        elapsed += duration
    figure = go.Figure(
        go.Scatter(
            x=times,
            y=intervals,
            mode="lines",
            line={"width": 2, "color": PRIMARY},
            customdata=labels,
            hovertemplate="%{customdata}<br>t = %{x:.4g} s<br>dt = %{y:.3g} s<extra></extra>",
        )
    )
    total = sum(segment.count for segment in segments)
    figure.update_layout(
        title=f"{clock}: {total:,} samples in segments (npts = {npts})",
        xaxis_title="time from start of timer (s)",
        yaxis_title="sample interval dt (s)",
        yaxis_type="log",
    )
    return figure


def array_figure(value: str) -> go.Figure:
    """Plot a numeric array as a line against its index."""
    numbers = parse_numeric_array(value)
    figure = go.Figure(
        go.Scatter(
            x=list(range(len(numbers))),
            y=numbers,
            mode="lines+markers",
            line={"width": 2, "color": PRIMARY},
            marker={"size": 8},
            hovertemplate="index %{x}<br>value = %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"{len(numbers)} values", xaxis_title="index", yaxis_title="value"
    )
    return figure


def counts_figure(series: pd.Series, title: str, limit: int = 40) -> go.Figure:
    """Plot a horizontal bar chart of value counts."""
    counts = series.value_counts().head(limit)
    if counts.empty:
        return empty_figure("No values")
    labels = [str(label) if str(label).strip() else "(blank)" for label in counts.index]
    figure = go.Figure(
        go.Bar(
            x=counts.values,
            y=labels,
            orientation="h",
            marker={"color": PRIMARY, "cornerradius": 4},
            hovertemplate="%{y}<br>%{x} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="number of keys",
        yaxis={"autorange": "reversed", "automargin": True},
        bargap=0.25,
    )
    return figure


def path_treemap(paths: pd.Series, title: str) -> go.Figure:
    """Show the directory tree of paths as a treemap. Size is the number of keys."""
    counts: dict[str, int] = {}
    for path in paths:
        parts = [part for part in str(path).strip().split("/") if part]
        if not str(path).startswith("/") and len(parts) == 1:
            parts = ["(file names)", *parts]
        node = ""
        for part in parts:
            node = f"{node}/{part}"
            counts[node] = counts.get(node, 0) + 1
    if not counts:
        return empty_figure("No paths")
    nodes = sorted(counts, key=lambda n: (n.count("/"), -counts[n]))[:MAX_PATH_NODES]
    keep = set(nodes)
    ids, labels, parents, values = [], [], [], []
    for node in nodes:
        parent = node.rsplit("/", 1)[0]
        if parent and parent not in keep:
            continue
        ids.append(node)
        labels.append(node.rsplit("/", 1)[1])
        parents.append(parent)
        values.append(counts[node])
    figure = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            maxdepth=4,
            marker={"colorscale": SEQUENTIAL, "colors": values, "line": {"width": 2}},
            hovertemplate="%{id}<br>%{value} keys<extra></extra>",
        )
    )
    figure.update_layout(title=title, margin={"l": 8, "r": 8, "t": 40, "b": 8})
    return figure
