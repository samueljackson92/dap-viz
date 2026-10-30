"""Waveforms tab: inline waveform DSL, timers and waveform references."""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, dcc, html

from dap_viz.classify import Category, Waveform, parse_dsl_waveform
from dap_viz.views import figures
from dap_viz.views.common import MAX_SERIES, graph


def parsed_waveforms(frame: pd.DataFrame) -> dict[str, Waveform]:
    """Parse all inline waveforms. Keep only the waveforms that parse."""
    rows = frame[frame["category"] == str(Category.DSL_WAVEFORM)]
    parsed = {
        key: parse_dsl_waveform(value) for key, value in zip(rows["key"], rows["value"])
    }
    return {key: wave for key, wave in parsed.items() if wave is not None}


def default_selection(waves: dict[str, Waveform]) -> list[str]:
    """Select the requested heating powers first, then the most detailed waveforms."""
    ranked = sorted(
        waves,
        key=lambda k: (not k.startswith("sl/"), -len(waves[k].times)),
    )
    return [k for k in ranked if len(waves[k].times) > 2][:4]


def layout(frame: pd.DataFrame) -> html.Div:
    """Make the waveforms tab."""
    waves = parsed_waveforms(frame)
    table = [
        {
            "key": key,
            "name": wave.name,
            "target": wave.target,
            "points": len(wave.times),
            "t_start": min(wave.times),
            "t_end": max(wave.times),
            "peak": max(wave.values, key=abs),
            "comment": wave.comment,
        }
        for key, wave in waves.items()
    ]
    timers = frame[frame["category"] == str(Category.DSL_TIMER)]
    refs = frame[frame["category"] == str(Category.WAVEFORM_REF)]
    ref_dirs = refs["value"].str.strip().str.split("/").str[0].str.upper()
    return html.Div(
        [
            html.H5(f"Inline waveforms ({len(waves)})"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="wf-keys",
                            options=[{"label": k, "value": k} for k in sorted(waves)],
                            value=default_selection(waves),
                            multi=True,
                            placeholder=f"Select up to {MAX_SERIES} waveforms",
                        ),
                        md=9,
                    ),
                    dbc.Col(
                        dbc.Switch(
                            id="wf-normalise",
                            label="Scale each to its peak",
                            value=False,
                        ),
                        md=3,
                    ),
                ],
                className="g-2 mb-2",
            ),
            dcc.Graph(id="wf-graph", style={"height": "460px"}),
            html.Div(
                "Waveforms in different units share one axis only when scaled to their peak.",
                className="small text-muted mb-2",
            ),
            dag.AgGrid(
                id="wf-table",
                rowData=table,
                columnDefs=[
                    {
                        "field": "key",
                        "flex": 2,
                        "checkboxSelection": True,
                        "cellClass": "font-monospace",
                    },
                    {"field": "name", "flex": 2},
                    {"field": "target", "flex": 1},
                    {"field": "points", "width": 90},
                    {"field": "t_start", "width": 100},
                    {"field": "t_end", "width": 100},
                    {"field": "peak", "width": 110},
                    {"field": "comment", "flex": 1},
                ],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                dashGridOptions={
                    "rowSelection": "multiple",
                    "suppressRowClickSelection": True,
                },
                style={"height": "320px"},
                className="ag-theme-alpine",
            ),
            html.H5(f"Timers ({len(timers)})", className="mt-4"),
            dcc.Dropdown(
                id="wf-timer",
                options=[{"label": k, "value": k} for k in timers["key"]],
                value=timers["key"].iloc[0] if len(timers) else None,
                clearable=False,
            ),
            dcc.Graph(id="wf-timer-graph", style={"height": "380px"}),
            html.H5(f"Waveform references ({len(refs)})", className="mt-4"),
            dbc.Row(
                [
                    dbc.Col(
                        graph(
                            figures.counts_figure(ref_dirs, "References by directory"),
                            420,
                        ),
                        lg=5,
                    ),
                    dbc.Col(
                        dag.AgGrid(
                            rowData=refs[["key", "value"]].to_dict("records"),
                            columnDefs=[
                                {
                                    "field": "key",
                                    "flex": 1,
                                    "cellClass": "font-monospace",
                                },
                                {
                                    "field": "value",
                                    "flex": 1,
                                    "cellClass": "font-monospace",
                                },
                            ],
                            defaultColDef={
                                "sortable": True,
                                "filter": True,
                                "resizable": True,
                            },
                            style={"height": "420px"},
                            className="ag-theme-alpine",
                        ),
                        lg=7,
                    ),
                ]
            ),
        ]
    )


def register(app: Dash, frame: pd.DataFrame) -> None:
    """Add the waveform callbacks."""
    waves = parsed_waveforms(frame)
    timers = frame[frame["category"] == str(Category.DSL_TIMER)].set_index("key")[
        "value"
    ]

    @app.callback(
        Output("wf-graph", "figure"),
        Input("wf-keys", "value"),
        Input("wf-normalise", "value"),
    )
    def plot_waveforms(keys, normalise):
        keys = (keys or [])[:MAX_SERIES]
        figure = figures.waveforms_figure(
            [(k, waves[k]) for k in keys], bool(normalise)
        )
        figure.update_layout(height=460)
        return figure

    @app.callback(
        Output("wf-keys", "value", allow_duplicate=True),
        Input("wf-table", "selectedRows"),
        prevent_initial_call=True,
    )
    def select_from_table(selected):
        return [row["key"] for row in (selected or [])][:MAX_SERIES]

    @app.callback(Output("wf-timer-graph", "figure"), Input("wf-timer", "value"))
    def plot_timer(key):
        figure = (
            figures.timer_figure(timers.get(key, ""))
            if key
            else figures.empty_figure("No timer")
        )
        figure.update_layout(height=380)
        return figure
