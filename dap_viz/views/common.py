"""Shared figure style and helpers for the views."""

import json
from typing import Any

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from dash import dcc, html

# Categorical slots in fixed order (reference palette, light mode).
SERIES = [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
]
MAX_SERIES = len(SERIES)
PRIMARY = SERIES[0]
HIGHLIGHT = SERIES[1]
SEQUENTIAL = [
    [0.0, "#cde2fb"],
    [0.25, "#86b6ef"],
    [0.5, "#3987e5"],
    [0.75, "#1c5cab"],
    [1.0, "#0d366b"],
]
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"

pio.templates["dap"] = go.layout.Template(
    layout=go.Layout(
        font={
            "family": "Inter, system-ui, sans-serif",
            "size": 12,
            "color": TEXT_PRIMARY,
        },
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=SERIES,
        margin={"l": 56, "r": 16, "t": 40, "b": 48},
        xaxis={"gridcolor": GRID, "zeroline": False, "linecolor": GRID},
        yaxis={"gridcolor": GRID, "zeroline": False, "linecolor": GRID},
        hoverlabel={"bgcolor": "white", "font": {"color": TEXT_PRIMARY}},
        title={"font": {"size": 14, "color": TEXT_PRIMARY}, "x": 0, "xanchor": "left"},
        legend={"orientation": "h", "y": -0.2},
    )
)
pio.templates.default = "dap"

GRAPH_CONFIG: Any = {"displaylogo": False, "toImageButtonOptions": {"format": "svg"}}


def loading(*children: Any) -> dcc.Loading:
    """Show a spinner over the children while a callback makes their data."""
    return dcc.Loading(
        list(children),
        type="circle",
        color=PRIMARY,
        delay_show=200,
        overlay_style={"visibility": "visible", "opacity": 0.4},
    )


def graph(figure: go.Figure, height: int = 400, **kwargs) -> dcc.Graph:
    """Make a dcc.Graph with the shared configuration."""
    figure.update_layout(height=height)
    return dcc.Graph(figure=figure, config=GRAPH_CONFIG, **kwargs)


def empty_figure(message: str) -> go.Figure:
    """Make a figure that shows only a message."""
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        showarrow=False,
        font={"color": TEXT_SECONDARY, "size": 14},
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure


def options(values: list[str], counts: pd.Series | None = None) -> list[dict]:
    """Make dropdown options. Add the count to the label when known."""
    if counts is None:
        return [{"label": value, "value": value} for value in values]
    return [{"label": f"{value} ({counts[value]})", "value": value} for value in values]


def stat_card(label: str, value: str | int) -> dbc.Card:
    """Make a small card with one headline number."""
    text = f"{value:,}" if isinstance(value, int) else value
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="text-muted small"),
                html.Div(text, className="fs-3 fw-semibold"),
            ]
        ),
        className="h-100",
    )


def pre(text: str) -> html.Pre:
    """Show raw text in a scroll box."""
    return html.Pre(text, className="raw-value")


def to_json(value: object) -> str:
    """Format an object as indented JSON for display."""
    return json.dumps(value, indent=2, default=str)


# Category groups for colour. Eight groups fit the categorical palette, so
# each group keeps one fixed colour. "Empty" is neutral grey: it has no data.
NEUTRAL = "#b4b2a9"
CATEGORY_GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    ("Numeric", SERIES[0], ("numeric", "numeric_array")),
    ("Categorical", SERIES[1], ("categorical",)),
    ("Text & names", SERIES[2], ("text", "identifier")),
    ("Paths & references", SERIES[3], ("filepath", "signal_path", "waveform_ref")),
    ("DSL", SERIES[4], ("dsl_waveform", "dsl_config", "dsl_typed_list", "dsl_timer")),
    ("Date & hex", SERIES[5], ("datetime", "hex")),
    ("Error", SERIES[7], ("error",)),
    ("Empty", NEUTRAL, ("empty",)),
]
GROUP_OF = {c: name for name, _, cats in CATEGORY_GROUPS for c in cats}
GROUP_COLOR = {name: color for name, color, _ in CATEGORY_GROUPS}
CATEGORY_COLOR = {c: GROUP_COLOR[GROUP_OF[c]] for c in GROUP_OF}
