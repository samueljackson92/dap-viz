"""Overview tab: counts by category and by system."""

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html

from dap_viz.classify import CATEGORY_DESCRIPTIONS, Category
from dap_viz.views.common import PRIMARY, SEQUENTIAL, graph, stat_card
from dap_viz.views.detail import small_grid

TOP_SYSTEMS = 30
ROOT = "all"
SEPARATOR = "|"


def category_bar(frame: pd.DataFrame) -> go.Figure:
    counts = frame["category"].value_counts()
    figure = go.Figure(
        go.Bar(
            x=counts.values,
            y=counts.index,
            orientation="h",
            marker={"color": PRIMARY, "cornerradius": 4},
            text=[f"{v:,}" for v in counts.values],
            textposition="outside",
            hovertemplate="%{y}<br>%{x:,} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title="Keys in each category",
        xaxis_type="log",
        xaxis_title="number of keys (log scale)",
        yaxis={"autorange": "reversed"},
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


def system_treemap(frame: pd.DataFrame) -> go.Figure:
    """Show systems, then categories, then key families as a treemap."""
    families = frame.value_counts(["system", "category", "family"]).reset_index(name="n")
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
    paths = [node.replace(SEPARATOR, " › ") for node in ids]
    figure = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=paths,
            branchvalues="total",
            maxdepth=2,
            marker={"colorscale": SEQUENTIAL, "colors": values, "line": {"width": 2}},
            hovertemplate="%{customdata}<br>%{value:,} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title="Systems › categories › key families. Click a box to open it and list its keys",
        margin={"l": 8, "r": 8, "t": 40, "b": 8},
    )
    return figure


def system_category_heatmap(frame: pd.DataFrame) -> go.Figure:
    top = frame["system"].value_counts().head(TOP_SYSTEMS).index
    table = pd.crosstab(
        frame.loc[frame["system"].isin(top), "system"], frame["category"]
    ).reindex(top)
    figure = go.Figure(
        go.Heatmap(
            z=table.values,
            x=table.columns,
            y=table.index,
            colorscale=SEQUENTIAL,
            xgap=2,
            ygap=2,
            hovertemplate="%{y} · %{x}<br>%{z:,} keys<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"Categories in the {TOP_SYSTEMS} largest systems",
        yaxis={"autorange": "reversed", "type": "category"},
    )
    return figure


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
                    dbc.Col(graph(category_bar(frame), 520), md=5),
                    dbc.Col(graph(system_treemap(frame), 520), md=7),
                ]
            ),
            graph(system_category_heatmap(frame), 720),
            html.H5("Category rules", className="mt-3"),
            small_grid(descriptions, ["category", "keys", "description"], height=560),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """The overview tab has no callbacks."""
