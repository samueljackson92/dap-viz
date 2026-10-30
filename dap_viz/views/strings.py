"""Categorical and text tab: label counts and a list of free text."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from dap_viz.classify import Category
from dap_viz.views import figures
from dap_viz.views.common import SEQUENTIAL, graph, options

TOP_VALUES = 25
TOP_SYSTEMS = 25
TEXT_CATEGORIES = [str(Category.TEXT), str(Category.IDENTIFIER), str(Category.DATETIME)]


def value_system_heatmap(rows: pd.DataFrame) -> go.Figure:
    values = rows["value"].str.strip()
    top_values = values.value_counts().head(TOP_VALUES).index
    top_systems = rows["system"].value_counts().head(TOP_SYSTEMS).index
    keep = values.isin(top_values) & rows["system"].isin(top_systems)
    table = pd.crosstab(values[keep], rows.loc[keep, "system"]).reindex(
        index=top_values, columns=top_systems, fill_value=0
    )
    figure = go.Figure(
        go.Heatmap(
            z=table.values.astype(float),
            x=list(table.columns),
            y=list(table.index),
            colorscale=SEQUENTIAL,
            xgap=2,
            ygap=2,
            hovertemplate="value %{y}<br>system %{x}<br>%{z} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"Most common {TOP_VALUES} labels in the {TOP_SYSTEMS} systems that use labels most",
        yaxis={"autorange": "reversed", "type": "category", "automargin": True},
        xaxis={"type": "category"},
    )
    return figure


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the categorical and text tab."""
    labels = frame[frame["category"] == str(Category.CATEGORICAL)]
    family_counts = labels["family"].value_counts()
    texts = frame[frame["category"].isin(TEXT_CATEGORIES)]
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Key family with labels"),
                            dcc.Dropdown(
                                id="st-family",
                                options=options(
                                    list(family_counts.index), family_counts
                                ),
                                value=family_counts.index[0],
                                clearable=False,
                            ),
                            dcc.Graph(id="st-family-graph", style={"height": "460px"}),
                        ],
                        lg=6,
                    ),
                    dbc.Col(
                        graph(
                            figures.counts_figure(
                                labels["value"].str.strip(),
                                "Most common labels in the file",
                                30,
                            ),
                            540,
                        ),
                        lg=6,
                    ),
                ]
            ),
            graph(value_system_heatmap(labels), 640),
            html.H5(
                f"Text, identifiers and dates ({len(texts):,} keys)", className="mt-3"
            ),
            dag.AgGrid(
                rowData=texts[["key", "category", "value"]].to_dict("records"),
                columnDefs=[
                    {"field": "key", "flex": 1, "cellClass": "font-monospace"},
                    {"field": "category", "width": 120},
                    {"field": "value", "flex": 3, "wrapText": True, "autoHeight": True},
                ],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                dashGridOptions={
                    "enableCellTextSelection": True,
                    "quickFilterText": "",
                },
                style={"height": "600px"},
                className="ag-theme-alpine",
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the categorical callbacks."""
    labels = frame[frame["category"] == str(Category.CATEGORICAL)]

    @app.callback(Output("st-family-graph", "figure"), Input("st-family", "value"))
    def plot_family(family):
        values = labels.loc[labels["family"] == family, "value"].str.strip()
        figure = figures.counts_figure(values, f"Labels in {family}")
        figure.update_layout(height=460)
        return figure
