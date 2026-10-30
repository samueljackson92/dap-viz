"""Config blocks tab: compare MARTe/GAM blocks and typed lists in one family."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from dap_viz.classify import (
    NUMBER_RE,
    Category,
    flatten_config,
    parse_config_block,
    parse_typed_list,
)
from dap_viz.views import figures
from dap_viz.views.common import PRIMARY, SEQUENTIAL, empty_figure, options


def config_table(frame: pd.DataFrame, family: str) -> pd.DataFrame:
    """Make one row for each block in the family and one column for each field."""
    rows = frame[
        (frame["family"] == family) & (frame["category"] == str(Category.DSL_CONFIG))
    ]
    rows = rows.sort_values("indices")
    records = [
        {"key": key, **flatten_config(parse_config_block(value))}
        for key, value in zip(rows["key"], rows["value"])
    ]
    return pd.DataFrame(records)


def numeric_fields(table: pd.DataFrame) -> list[str]:
    """Return the fields where all values are numbers."""
    fields = []
    for column in table.columns.drop("key", errors="ignore"):
        values = table[column].dropna().astype(str).str.strip()
        if len(values) and values.map(lambda v: bool(NUMBER_RE.match(v))).all():
            fields.append(column)
    return fields


def typed_list_figure(frame: pd.DataFrame, family: str) -> go.Figure:
    """Show the numeric items of each typed list in a family as a heatmap."""
    rows = frame[
        (frame["family"] == family)
        & (frame["category"] == str(Category.DSL_TYPED_LIST))
    ]
    if rows.empty:
        return empty_figure("No typed lists")
    rows = rows.sort_values("indices")
    z, text = [], []
    for value in rows["value"]:
        items = parse_typed_list(value)
        z.append(
            [item.value if isinstance(item.value, float) else None for item in items]
        )
        text.append([f"{item.kind} {item.value}" for item in items])
    figure = go.Figure(
        go.Heatmap(
            z=z,
            y=list(rows["key"]),
            text=text,
            colorscale=SEQUENTIAL,
            xgap=2,
            ygap=2,
            hovertemplate="%{y}<br>item %{x}: %{text}<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"{family}: numeric items (R, I). Text items (C) are blank",
        xaxis_title="item position",
        yaxis={"autorange": "reversed", "type": "category", "automargin": True},
    )
    return figure


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the config blocks tab."""
    blocks = frame[frame["category"] == str(Category.DSL_CONFIG)]
    block_families = blocks["family"].value_counts()
    lists = frame[frame["category"] == str(Category.DSL_TYPED_LIST)]
    list_families = lists["family"].value_counts()
    return html.Div(
        [
            html.H5(f"Configuration blocks ({len(blocks)} keys)"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="cf-family",
                            options=options(list(block_families.index), block_families),
                            value=block_families.index[0]
                            if len(block_families)
                            else None,
                            clearable=False,
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dcc.Dropdown(id="cf-field", placeholder="Numeric field"), md=6
                    ),
                ],
                className="g-2 mb-2",
            ),
            dag.AgGrid(
                id="cf-table",
                defaultColDef={
                    "sortable": True,
                    "filter": True,
                    "resizable": True,
                    "minWidth": 110,
                },
                dashGridOptions={
                    "enableCellTextSelection": True,
                    "suppressFieldDotNotation": True,
                },
                style={"height": "380px"},
                className="ag-theme-alpine",
            ),
            dcc.Graph(id="cf-field-graph", style={"height": "400px"}),
            html.H5(f"Typed lists ({len(lists)} keys)", className="mt-4"),
            dcc.Dropdown(
                id="cf-list-family",
                options=options(list(list_families.index), list_families),
                value=list_families.index[0] if len(list_families) else None,
                clearable=False,
            ),
            dcc.Graph(id="cf-list-graph", style={"height": "560px"}),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the config block callbacks."""

    @app.callback(
        Output("cf-table", "rowData"),
        Output("cf-table", "columnDefs"),
        Output("cf-field", "options"),
        Output("cf-field", "value"),
        Input("cf-family", "value"),
    )
    def update_table(family):
        table = config_table(frame, family) if family else pd.DataFrame()
        columns = [
            {"field": c, "pinned": "left", "cellClass": "font-monospace"}
            if c == "key"
            else {"field": c}
            for c in table.columns
        ]
        fields = numeric_fields(table)
        return (
            table.fillna("").to_dict("records"),
            columns,
            [{"label": f, "value": f} for f in fields],
            fields[0] if fields else None,
        )

    @app.callback(
        Output("cf-field-graph", "figure"),
        Input("cf-family", "value"),
        Input("cf-field", "value"),
    )
    def plot_field(family, field):
        if not family or not field:
            return empty_figure("This family has no numeric fields")
        table = config_table(frame, family)
        values = pd.to_numeric(table[field], errors="coerce")
        figure = go.Figure(
            go.Bar(
                x=table["key"],
                y=values,
                marker={"color": PRIMARY, "cornerradius": 4},
                hovertemplate="%{x}<br>" + field + " = %{y}<extra></extra>",
            )
        )
        figure.update_layout(
            title=f"{field} in each block of {family}", yaxis_title=field, height=400
        )
        return figure

    @app.callback(Output("cf-list-graph", "figure"), Input("cf-list-family", "value"))
    def plot_lists(family):
        figure = (
            typed_list_figure(frame, family) if family else figures.empty_figure("None")
        )
        figure.update_layout(height=560)
        return figure
