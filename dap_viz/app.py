"""Make the Dash application."""

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html

from dap_viz.model import build_frame
from dap_viz.parser import pulse_number, read_dap
from dap_viz.views import (
    config,
    explorer,
    issues,
    numeric,
    overview,
    paths,
    strings,
    waveforms,
)

ASSETS = Path(__file__).parent / "assets"


def create_app(frame: pd.DataFrame, pulse: int | None = None, source: str = "") -> Dash:
    """Make the Dash application for one DAP data frame."""
    app = Dash(
        __name__,
        title=f"DAP {pulse}" if pulse else "DAP viewer",
        external_stylesheets=[dbc.themes.FLATLY],
        assets_folder=str(ASSETS),
        suppress_callback_exceptions=True,
    )
    tabs = [
        ("Overview", overview.layout(frame, pulse)),
        ("Explorer", explorer.layout(frame)),
        ("Numerics", numeric.layout(frame)),
        ("Categorical & text", strings.layout(frame)),
        ("Waveforms (DSL)", waveforms.layout(frame)),
        ("Config blocks", config.layout(frame)),
        ("File paths", paths.layout(frame)),
        ("Issues", issues.layout(frame)),
    ]
    app.layout = dbc.Container(
        [
            html.Div(
                [
                    html.H3(f"DAP Viz — pulse {pulse}" if pulse else "JET DAP viewer"),
                    html.Div(source, className="text-muted small font-monospace"),
                ],
                className="my-3",
            ),
            dbc.Tabs(
                [
                    dbc.Tab(html.Div(body, className="pt-3"), label=label, tab_id=label)
                    for label, body in tabs
                ],
                active_tab="Overview",
            ),
        ],
        fluid=True,
        className="pb-5",
    )
    for view in (
        overview,
        explorer,
        numeric,
        strings,
        waveforms,
        config,
        paths,
        issues,
    ):
        view.register(app, frame)
    return app


def app_from_file(path: str | Path) -> Dash:
    """Read a DAP file and make the Dash application."""
    frame = build_frame(read_dap(path))
    return create_app(frame, pulse_number(path), str(Path(path).resolve()))
