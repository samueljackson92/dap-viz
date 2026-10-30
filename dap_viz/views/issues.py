"""Issues tab: read errors and empty values."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html

from dap_viz.classify import Category
from dap_viz.views import figures
from dap_viz.views.common import graph


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the issues tab."""
    errors = frame[frame["category"] == str(Category.ERROR)]
    empty = frame[frame["category"] == str(Category.EMPTY)]
    return html.Div(
        [
            html.H5(f"Read errors ({len(errors)} keys)"),
            dbc.Row(
                [
                    dbc.Col(
                        graph(
                            figures.counts_figure(
                                errors["value"].str.strip(), "Error messages"
                            ),
                            380,
                        ),
                        lg=6,
                    ),
                    dbc.Col(
                        graph(
                            figures.counts_figure(errors["system"], "Errors by system"),
                            380,
                        ),
                        lg=6,
                    ),
                ]
            ),
            dag.AgGrid(
                rowData=errors[["key", "value", "line"]].to_dict("records"),
                columnDefs=[
                    {"field": "key", "flex": 1, "cellClass": "font-monospace"},
                    {"field": "value", "flex": 2},
                    {"field": "line", "width": 100},
                ],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                style={"height": "360px"},
                className="ag-theme-alpine",
            ),
            html.H5(f"Empty values ({len(empty):,} keys)", className="mt-4"),
            graph(
                figures.counts_figure(empty["system"], "Empty values by system", 40),
                640,
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """The issues tab has no callbacks."""
