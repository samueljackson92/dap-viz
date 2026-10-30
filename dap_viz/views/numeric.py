"""Numerics tab: plots of numeric key families and value distributions."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from dap_viz.classify import Category
from dap_viz.views import figures
from dap_viz.views.common import PRIMARY, empty_figure, options


def numeric_rows(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["category"] == str(Category.NUMERIC)]


def family_summary(rows: pd.DataFrame) -> pd.DataFrame:
    """Return one row for each family: count, range and kind."""
    grouped = rows.groupby("family")
    summary = pd.DataFrame(
        {
            "keys": grouped.size(),
            "distinct": grouped["number"].nunique(),
            "min": grouped["number"].min(),
            "max": grouped["number"].max(),
            "mean": grouped["number"].mean().round(6),
            "kind": grouped["numeric_kind"].agg(lambda s: "/".join(sorted(set(s)))),
        }
    )
    return summary.sort_values("keys", ascending=False).reset_index()


def histogram(values: pd.Series, log_y: bool, symlog_x: bool) -> go.Figure:
    if values.empty:
        return empty_figure("No numeric values")
    data = np.sign(values) * np.log10(1 + values.abs()) if symlog_x else values
    figure = go.Figure(
        go.Histogram(
            x=data,
            nbinsx=80,
            marker={"color": PRIMARY, "line": {"width": 1, "color": "white"}},
            hovertemplate="%{x}<br>%{y} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"Distribution of {len(values):,} values",
        xaxis_title="sign(v)·log10(1+|v|)" if symlog_x else "value",
        yaxis_title="number of keys",
        yaxis_type="log" if log_y else "linear",
        bargap=0.05,
    )
    return figure


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the numerics tab."""
    rows = numeric_rows(frame)
    system_counts = rows["system"].value_counts()
    first = system_counts.index[0]
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("System"),
                            dcc.Dropdown(
                                id="nu-system",
                                options=options(
                                    list(system_counts.index), system_counts
                                ),
                                value=first,
                                clearable=False,
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Key family"),
                            dcc.Dropdown(id="nu-family", clearable=False),
                        ],
                        md=5,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Histogram"),
                            dbc.Checklist(
                                id="nu-scale",
                                options=[
                                    {"label": "log count", "value": "log"},
                                    {"label": "symlog value", "value": "symlog"},
                                ],
                                value=["log", "symlog"],
                                inline=True,
                                switch=True,
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="g-2 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(id="nu-family-graph", style={"height": "480px"}), lg=7
                    ),
                    dbc.Col(
                        dcc.Graph(id="nu-histogram", style={"height": "480px"}), lg=5
                    ),
                ]
            ),
            html.H6(
                "Families in this system (click a row to plot it)", className="mt-2"
            ),
            dag.AgGrid(
                id="nu-summary",
                columnDefs=[
                    {"field": "family", "flex": 2, "cellClass": "font-monospace"},
                    {"field": "keys", "width": 90},
                    {"field": "distinct", "width": 100},
                    {"field": "min", "flex": 1},
                    {"field": "max", "flex": 1},
                    {"field": "mean", "flex": 1},
                    {"field": "kind", "flex": 1},
                ],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                dashGridOptions={"rowSelection": "single"},
                style={"height": "360px"},
                className="ag-theme-alpine",
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the numerics callbacks."""
    rows = numeric_rows(frame)

    @app.callback(
        Output("nu-family", "options"),
        Output("nu-family", "value"),
        Output("nu-summary", "rowData"),
        Input("nu-system", "value"),
    )
    def update_families(system):
        summary = family_summary(rows[rows["system"] == system])
        family_options = [
            {"label": f"{f} ({n})", "value": f}
            for f, n in zip(summary["family"], summary["keys"], strict=True)
        ]
        first = summary["family"].iloc[0] if len(summary) else None
        return family_options, first, summary.to_dict("records")

    @app.callback(
        Output("nu-family", "value", allow_duplicate=True),
        Input("nu-summary", "selectedRows"),
        prevent_initial_call=True,
    )
    def pick_family(selected):
        return selected[0]["family"] if selected else None

    @app.callback(Output("nu-family-graph", "figure"), Input("nu-family", "value"))
    def plot_family(family):
        if not family:
            return empty_figure("Select a family")
        figure = figures.family_figure(rows, family)
        figure.update_layout(height=480)
        return figure

    @app.callback(
        Output("nu-histogram", "figure"),
        Input("nu-system", "value"),
        Input("nu-scale", "value"),
    )
    def plot_histogram(system, scale):
        values = rows.loc[rows["system"] == system, "number"]
        figure = histogram(values, "log" in scale, "symlog" in scale)
        figure.update_layout(
            title=f"{system}: distribution of {len(values):,} values", height=480
        )
        return figure
