"""File paths tab: the directory tree of all paths and signal paths."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, dcc, html

from dap_viz.classify import Category
from dap_viz.views import figures

PATH_CATEGORIES = [str(Category.FILEPATH), str(Category.SIGNAL_PATH)]


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the file paths tab."""
    rows = frame[frame["category"].isin(PATH_CATEGORIES)]
    unique = rows.groupby(rows["value"].str.strip()).agg(
        keys=("key", "size"), category=("category", "first"), example=("key", "first")
    )
    unique = unique.reset_index().rename(columns={"value": "path"})
    return html.Div(
        [
            dbc.RadioItems(
                id="pa-category",
                options=[
                    {"label": "File paths", "value": str(Category.FILEPATH)},
                    {"label": "Signal paths", "value": str(Category.SIGNAL_PATH)},
                ],
                value=str(Category.FILEPATH),
                inline=True,
                className="mb-2",
            ),
            dcc.Graph(id="pa-treemap", style={"height": "620px"}),
            html.H5(f"Distinct paths ({len(unique):,})", className="mt-3"),
            dag.AgGrid(
                rowData=unique.to_dict("records"),
                columnDefs=[
                    {"field": "path", "flex": 3, "cellClass": "font-monospace"},
                    {"field": "category", "width": 120},
                    {"field": "keys", "width": 90, "sort": "desc"},
                    {"field": "example", "headerName": "example key", "flex": 2},
                ],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                dashGridOptions={"enableCellTextSelection": True},
                style={"height": "480px"},
                className="ag-theme-alpine",
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the file path callbacks."""

    @app.callback(Output("pa-treemap", "figure"), Input("pa-category", "value"))
    def plot_tree(category):
        values = frame.loc[frame["category"] == category, "value"]
        figure = figures.path_treemap(
            values,
            f"{len(values):,} keys. Click a box to open it; click the top bar to go back",
        )
        figure.update_layout(height=620)
        return figure
