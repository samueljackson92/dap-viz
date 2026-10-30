from dap_viz.model import build_frame
from dap_viz.parser import Record
from dap_viz.views.common import CATEGORY_COLOR
from dap_viz.views.overview import (
    ROOT,
    node_id,
    parent_node_id,
    parse_node_id,
    system_bar,
)


def test_node_id_round_trip():
    node = node_id("Sc", "numeric", "Sc/NormCtrl.c#w#")
    assert parse_node_id(node) == ("Sc", "numeric", "Sc/NormCtrl.c#w#")
    assert parse_node_id(node_id("Sc", "numeric")) == ("Sc", "numeric", None)
    assert parse_node_id("Sc") == ("Sc", None, None)
    assert parse_node_id(ROOT) == (None, None, None)
    assert parse_node_id(None) == (None, None, None)


def test_parent_node_id():
    assert parent_node_id(node_id("Sc", "numeric", "Sc/X#")) == node_id("Sc", "numeric")
    assert parent_node_id(node_id("Sc", "numeric")) == "Sc"
    assert parent_node_id("Sc") == ROOT
    assert parent_node_id(ROOT) == ROOT


def test_system_bar():
    frame = build_frame(
        [
            Record("Sc/W.1", "1.5", 1),
            Record("Sc/W.2", "2.5", 2),
            Record("Sc/Path", "/jet/pm/x/y.cfg", 3),
            Record("pf/Gain", "3", 4),
        ]
    )
    bars = {t.name: t for t in system_bar(frame).data if t.type == "bar"}
    assert set(bars) == {"numeric", "filepath"}
    assert list(bars["numeric"].y) == ["Sc", "pf"]
    assert list(bars["numeric"].x) == [2, 1]
    assert list(bars["filepath"].x) == [1, 0]
    assert bars["filepath"].marker.color == CATEGORY_COLOR["filepath"]
