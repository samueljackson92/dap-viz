"""Detail panel for one key. The view depends on the category of the value."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

from dap_viz.classify import (
    CATEGORY_DESCRIPTIONS,
    Category,
    flatten_config,
    parse_config_block,
    parse_typed_list,
)
from dap_viz.views import figures
from dap_viz.views.common import graph, pre, to_json


def small_grid(rows: list[dict], columns: list[str], height: int = 300) -> dag.AgGrid:
    """Make a small read-only grid."""
    return dag.AgGrid(
        rowData=rows,
        columnDefs=[{"field": c, "flex": 1} for c in columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        style={"height": f"{height}px"},
        className="ag-theme-alpine",
    )


def _facts(row: pd.Series, same_value: int, family_size: int) -> html.Dl:
    items = [
        (
            "Category",
            f"{row['category']} — {CATEGORY_DESCRIPTIONS[Category(row['category'])]}",
        ),
        ("System", row["system"]),
        ("Family", f"{row['family']} ({family_size} keys)"),
        ("Indices", ", ".join(map(str, row["indices"])) or "—"),
        ("Line in file", row["line"]),
        ("Keys with the same value", same_value),
    ]
    if row["numeric_kind"]:
        items.insert(1, ("Numeric kind", row["numeric_kind"]))
    children = []
    for term, value in items:
        children += [
            html.Dt(term, className="col-sm-4"),
            html.Dd(str(value), className="col-sm-8"),
        ]
    return html.Dl(children, className="row small mb-2")


def _body(frame: pd.DataFrame, row: pd.Series) -> list:
    category = Category(row["category"])
    key, value = row["key"], row["value"]
    if category == Category.NUMERIC:
        return [graph(figures.family_figure(frame, row["family"], highlight=key), 360)]
    if category == Category.NUMERIC_ARRAY:
        return [graph(figures.array_figure(value), 320)]
    if category == Category.DSL_WAVEFORM:
        return [graph(figures.waveform_figure(key, value), 340)]
    if category == Category.DSL_TIMER:
        return [graph(figures.timer_figure(value), 320)]
    if category == Category.DSL_CONFIG:
        flat = flatten_config(parse_config_block(value))
        rows = [{"field": k, "value": v} for k, v in flat.items()]
        return [
            small_grid(rows, ["field", "value"]),
            html.Details(
                [html.Summary("Parsed tree"), pre(to_json(parse_config_block(value)))]
            ),
        ]
    if category == Category.DSL_TYPED_LIST:
        rows = [
            {"position": i, "type": item.kind, "value": item.value}
            for i, item in enumerate(parse_typed_list(value))
        ]
        return [small_grid(rows, ["position", "type", "value"])]
    if category in (Category.FILEPATH, Category.SIGNAL_PATH, Category.WAVEFORM_REF):
        parts = [p for p in value.strip().split("/") if p]
        crumbs = dbc.Breadcrumb(items=[{"label": p} for p in parts])
        users = frame[frame["value"].str.strip() == value.strip()]["key"]
        return [
            crumbs,
            html.Div("Keys that use this value:", className="small text-muted"),
            pre("\n".join(users)),
        ]
    if category == Category.CATEGORICAL:
        family = frame[frame["family"] == row["family"]]["value"].str.strip()
        return [graph(figures.counts_figure(family, f"Values in {row['family']}"), 320)]
    return []


def render_detail(frame: pd.DataFrame, key: str | None) -> list:
    """Make the detail panel for one key."""
    if not key:
        return [html.P("Select a row to see the details.", className="text-muted")]
    match = frame[frame["key"] == key]
    if match.empty:
        return [html.P(f"Key {key} not found.", className="text-danger")]
    row = match.iloc[0]
    same_value = int((frame["value"] == row["value"]).sum())
    family_size = int((frame["family"] == row["family"]).sum())
    return [
        html.H5(key, className="font-monospace text-break"),
        _facts(row, same_value, family_size),
        html.Div("Raw value", className="small text-muted"),
        pre(row["value"] if row["value"] else "(empty)"),
        *_body(frame, row),
    ]
