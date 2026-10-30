"""Overview tab: counts by category and by system."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, ctx, dcc, html

from dap_viz.classify import CATEGORY_DESCRIPTIONS, Category
from dap_viz.views.common import (
    CATEGORY_COLOR,
    CATEGORY_GROUPS,
    SEQUENTIAL,
    SURFACE,
    graph,
    options,
    stat_card,
)
from dap_viz.views.detail import render_detail, small_grid
from dap_viz.views.explorer import grid_rows

TOP_SYSTEMS = 30
ROOT = "all"
SEPARATOR = "|"


def system_bar(frame: pd.DataFrame) -> go.Figure:
    """Show the largest systems as bars, with one coloured segment for each category."""
    top = frame["system"].value_counts().head(TOP_SYSTEMS).index
    table = pd.crosstab(
        frame.loc[frame["system"].isin(top), "system"], frame["category"]
    ).reindex(top)
    figure = go.Figure()
    # Categories of one colour group are next to each other in the bars.
    for _, _, categories in CATEGORY_GROUPS:
        for category in categories:
            if category not in table.columns:
                continue
            figure.add_trace(
                go.Bar(
                    x=table[category],
                    y=table.index,
                    name=category,
                    orientation="h",
                    marker={
                        "color": CATEGORY_COLOR[category],
                        "line": {"width": 1, "color": SURFACE},
                    },
                    customdata=[category] * len(table),
                    hovertemplate="%{y} · %{customdata}<br>%{x:,} keys<extra></extra>",
                )
            )
    totals = table.sum(axis=1)
    figure.add_trace(
        go.Scatter(
            x=totals,
            y=table.index,
            mode="text",
            text=[f" {v:,}" for v in totals],
            textposition="middle right",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.update_layout(
        title=f"Keys in the {TOP_SYSTEMS} largest systems. Click a bar to list its keys",
        barmode="stack",
        bargap=0.25,
        xaxis_title="number of keys",
        xaxis_range=[0, totals.max() * 1.15],
        yaxis={"autorange": "reversed", "type": "category"},
        legend={"orientation": "h", "y": -0.12, "font": {"size": 11}},
        margin={"l": 80, "r": 16, "t": 40, "b": 40},
    )
    return figure


def node_id(*parts: str) -> str:
    """Make a treemap node id from the system, category and family."""
    return SEPARATOR.join(parts)


def parse_node_id(node: str | None) -> tuple[str | None, str | None, str | None]:
    """Return the system, category and family of a treemap node id."""
    if not node or node == ROOT:
        return None, None, None
    parts = [*node.split(SEPARATOR), None, None]
    return parts[0], parts[1], parts[2]


def parent_node_id(node: str) -> str:
    """Return the id of the parent node in the treemap."""
    return node.rsplit(SEPARATOR, 1)[0] if SEPARATOR in node else ROOT


def system_treemap(frame: pd.DataFrame) -> go.Figure:
    """Show systems, then categories, then key families as a treemap."""
    families = frame.value_counts(["system", "category", "family"]).reset_index(
        name="n"
    )
    categories = families.groupby(["system", "category"])["n"].sum().reset_index()
    systems = categories.groupby("system")["n"].sum()
    ids = [ROOT, *systems.index]
    labels = ["all systems", *systems.index]
    parents = ["", *[ROOT] * len(systems)]
    values = [int(systems.sum()), *systems.values]
    ids += [node_id(s, c) for s, c in zip(categories["system"], categories["category"])]
    labels += list(categories["category"])
    parents += list(categories["system"])
    values += list(categories["n"])
    ids += [
        node_id(s, c, f)
        for s, c, f in zip(families["system"], families["category"], families["family"])
    ]
    labels += [f.split("/", 1)[-1] for f in families["family"]]
    parents += [node_id(s, c) for s, c in zip(families["system"], families["category"])]
    values += list(families["n"])
    figure = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            maxdepth=2,
            marker={"colorscale": SEQUENTIAL, "colors": values, "line": {"width": 2}},
            hovertemplate="%{currentPath}%{label}<br>%{value:,} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title="Systems › categories › key families. Click a box to open it and list its keys",
        margin={"l": 8, "r": 8, "t": 40, "b": 8},
    )
    return figure


def drill_down(frame: pd.DataFrame) -> dbc.Card:
    """Make the panel that lists the keys of one system, category or family."""
    system_counts = frame["system"].value_counts()
    category_counts = frame["category"].value_counts()
    selectors = dbc.Row(
        [
            dbc.Col(
                dcc.Dropdown(
                    id="ov-system",
                    options=options(
                        sorted(system_counts.index, key=str.lower), system_counts
                    ),
                    placeholder="System",
                ),
                md=3,
            ),
            dbc.Col(
                dcc.Dropdown(
                    id="ov-category",
                    options=options(list(category_counts.index), category_counts),
                    placeholder="All categories",
                ),
                md=3,
            ),
            dbc.Col(dcc.Dropdown(id="ov-family", placeholder="All families"), md=6),
        ],
        className="g-2 mb-2",
    )
    grid = dag.AgGrid(
        id="ov-grid",
        columnDefs=[
            {"field": "key", "flex": 2, "cellClass": "font-monospace"},
            {"field": "category", "flex": 1},
            {"field": "numeric_kind", "headerName": "kind", "width": 90},
            {"field": "value", "flex": 3, "cellClass": "font-monospace"},
        ],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        getRowId="params.data.key",
        dashGridOptions={"rowSelection": "single", "enableCellTextSelection": True},
        style={"height": "60vh"},
        className="ag-theme-alpine",
    )
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5("Keys in the selected group", className="mb-1"),
                html.Div(id="ov-path", className="small text-muted mb-2"),
                selectors,
                dbc.Row(
                    [
                        dbc.Col(grid, lg=7),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(id="ov-detail"), className="detail-card"
                            ),
                            lg=5,
                        ),
                    ],
                    className="g-2",
                ),
            ]
        ),
        className="my-3",
    )


def select_rows(
    frame: pd.DataFrame, system: str | None, category: str | None, family: str | None
) -> pd.DataFrame:
    """Return the keys of the selected group."""
    mask = pd.Series(True, index=frame.index)
    if system:
        mask &= frame["system"] == system
    if category:
        mask &= frame["category"] == category
    if family:
        mask &= frame["family"] == family
    return frame[mask].sort_values(["family", "indices"])


def layout(frame: pd.DataFrame, pulse: int | None) -> html.Div:
    """Make the overview tab."""
    descriptions = [
        {
            "category": str(category),
            "keys": int((frame["category"] == str(category)).sum()),
            "description": text,
        }
        for category, text in CATEGORY_DESCRIPTIONS.items()
    ]
    cards = [
        ("Pulse", str(pulse) if pulse else "—"),
        ("Keys", len(frame)),
        ("Systems", frame["system"].nunique()),
        ("Key families", frame["family"].nunique()),
        ("Categories", frame["category"].nunique()),
        ("Numeric keys", int((frame["category"] == Category.NUMERIC).sum())),
    ]
    return html.Div(
        [
            dbc.Row(
                [dbc.Col(stat_card(*card), md=2) for card in cards],
                className="g-2 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(graph(system_bar(frame), 720, id="ov-bar"), md=5),
                    dbc.Col(graph(system_treemap(frame), 720, id="ov-treemap"), md=7),
                ]
            ),
            drill_down(frame),
            html.H5("Category rules", className="mt-3"),
            small_grid(descriptions, ["category", "keys", "description"], height=560),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the drill-down callbacks."""

    @app.callback(
        Output("ov-system", "value"),
        Output("ov-category", "value"),
        Output("ov-family", "options"),
        Output("ov-family", "value"),
        Output("ov-grid", "rowData"),
        Output("ov-path", "children"),
        Input("ov-treemap", "clickData"),
        Input("ov-bar", "clickData"),
        Input("ov-system", "value"),
        Input("ov-category", "value"),
        Input("ov-family", "value"),
    )
    def drill(tree_click, bar_click, system, category, family):
        if ctx.triggered_id == "ov-treemap" and tree_click:
            point = tree_click["points"][0]
            # A click on the top bar of a zoomed treemap goes back to the parent.
            node = point.get("id") or ROOT
            if point.get("label") == point.get("entry"):
                node = parent_node_id(node)
            system, category, family = parse_node_id(node)
        elif ctx.triggered_id == "ov-bar" and bar_click:
            point = bar_click["points"][0]
            system, category, family = point["y"], point.get("customdata"), None
        elif ctx.triggered_id in ("ov-system", "ov-category"):
            family = None
        group = select_rows(frame, system, None, None)
        if category:
            group = group[group["category"] == category]
        family_counts = group["family"].value_counts()
        if family not in family_counts.index:
            family = None
        family_options = options(list(family_counts.index), family_counts)
        if not system and not category:
            hint = "Click a box in the treemap or select a system to list its keys."
            return None, None, [], None, [], hint
        rows = group[group["family"] == family] if family else group
        path = " › ".join(p for p in (system or "all systems", category, family) if p)
        return (
            system,
            category,
            family_options,
            family,
            grid_rows(rows),
            f"{path}: {len(rows):,} keys",
        )

    @app.callback(Output("ov-detail", "children"), Input("ov-grid", "selectedRows"))
    def show_detail(selected):
        return render_detail(frame, selected[0]["key"] if selected else None)
