"""Explorer tab: a grid of all keys with filters and a detail panel."""

import re

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, dcc, html

from dap_viz.views.common import options
from dap_viz.views.detail import render_detail

GRID_VALUE_LENGTH = 120
GRID_COLUMNS = ["key", "category", "numeric_kind", "value", "system"]


def grid_rows(frame: pd.DataFrame) -> list[dict]:
    """Make the grid rows. Long values are cut to keep the page fast."""
    rows = frame[GRID_COLUMNS].copy()
    rows["value"] = (
        rows["value"].str.slice(0, GRID_VALUE_LENGTH).str.replace("\n", " ⏎ ")
    )
    return rows.to_dict("records")


def filter_frame(
    frame: pd.DataFrame,
    categories: list[str] | None,
    systems: list[str] | None,
    search: str | None,
    target: str,
) -> pd.DataFrame:
    """Return the rows that match the filters. The search is a regular expression."""
    mask = pd.Series(True, index=frame.index)
    if categories:
        mask &= frame["category"].isin(categories)
    if systems:
        mask &= frame["system"].isin(systems)
    if search:
        try:
            pattern = re.compile(search, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
        columns = ["key", "value"] if target == "both" else [target]
        hit = pd.Series(False, index=frame.index)
        for column in columns:
            hit |= frame[column].str.contains(pattern, regex=True, na=False)
        mask &= hit
    return frame[mask]


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the explorer tab."""
    category_counts = frame["category"].value_counts()
    system_counts = frame["system"].value_counts()
    controls = dbc.Row(
        [
            dbc.Col(
                dcc.Dropdown(
                    id="ex-category",
                    options=options(list(category_counts.index), category_counts),
                    multi=True,
                    placeholder="All categories",
                ),
                md=3,
            ),
            dbc.Col(
                dcc.Dropdown(
                    id="ex-system",
                    options=options(
                        sorted(system_counts.index, key=str.lower), system_counts
                    ),
                    multi=True,
                    placeholder="All systems",
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Input(
                    id="ex-search",
                    placeholder="Search (regular expression)",
                    debounce=True,
                    type="search",
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Select(
                    id="ex-target",
                    options=[
                        {"label": "Key and value", "value": "both"},
                        {"label": "Key only", "value": "key"},
                        {"label": "Value only", "value": "value"},
                    ],
                    value="both",
                ),
                md=2,
            ),
        ],
        className="g-2 mb-2",
    )
    grid = dag.AgGrid(
        id="ex-grid",
        columnDefs=[
            {
                "field": "key",
                "flex": 2,
                "pinned": "left",
                "cellClass": "font-monospace",
            },
            {"field": "category", "flex": 1},
            {"field": "numeric_kind", "headerName": "kind", "width": 90},
            {"field": "value", "flex": 3, "cellClass": "font-monospace"},
            {"field": "system", "width": 110},
        ],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        getRowId="params.data.key",
        dashGridOptions={
            "rowSelection": "single",
            "animateRows": False,
            "enableCellTextSelection": True,
            "tooltipShowDelay": 300,
        },
        style={"height": "72vh"},
        className="ag-theme-alpine",
    )
    return html.Div(
        [
            controls,
            html.Div(id="ex-count", className="small text-muted mb-1"),
            dbc.Row(
                [
                    dbc.Col(grid, lg=7),
                    dbc.Col(
                        dbc.Card(dbc.CardBody(id="ex-detail"), className="detail-card"),
                        lg=5,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the explorer callbacks."""

    @app.callback(
        Output("ex-grid", "rowData"),
        Output("ex-count", "children"),
        Input("ex-category", "value"),
        Input("ex-system", "value"),
        Input("ex-search", "value"),
        Input("ex-target", "value"),
    )
    def update_grid(categories, systems, search, target):
        rows = filter_frame(frame, categories, systems, search, target or "both")
        return grid_rows(rows), f"{len(rows):,} of {len(frame):,} keys"

    @app.callback(Output("ex-detail", "children"), Input("ex-grid", "selectedRows"))
    def show_detail(selected):
        key = selected[0]["key"] if selected else None
        return render_detail(frame, key)
