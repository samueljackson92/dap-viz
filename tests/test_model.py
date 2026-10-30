from pathlib import Path

import pytest

from dap_viz.classify import Category
from dap_viz.model import build_frame, family_of
from dap_viz.parser import Record, read_dap

DATA = Path(__file__).parents[1] / "DAP-0103169.txt"


def test_family_of():
    assert family_of("Sc/NormCtrl.c3w12") == ("Sc/NormCtrl.c#w#", (3, 12))
    assert family_of("KM11/CurrentLevel_0_031") == ("KM11/CurrentLevel_#_#", (0, 31))
    assert family_of("l1/PulseNumber") == ("l1/PulseNumber", ())


def test_build_frame_categories_and_flags():
    records = [
        Record("vtm/LogicalTile.1.Material", "Be", 1),
        Record("vtm/LogicalTile.2.Material", "Be", 2),
        Record("vtm/LogicalTile.3.Material", "Be", 3),
        Record("vtm/LogicalTile.1.Name", "IWL:18", 4),
        Record("mc/PschedAuthor", "Hongjuan Sun", 5),
        Record("sl/isAHRequired", "1", 6),
        Record("sl/isEFCCRequired", "0", 7),
        Record("x/On.1", "0", 8),
        Record("x/On.2", "1", 9),
        Record("x/Gain", "2.5", 10),
    ]
    frame = build_frame(records).set_index("key")
    assert frame.loc["vtm/LogicalTile.1.Material", "category"] == Category.CATEGORICAL
    assert frame.loc["vtm/LogicalTile.1.Name", "category"] == Category.IDENTIFIER
    assert frame.loc["mc/PschedAuthor", "category"] == Category.TEXT
    assert frame.loc["x/On.1", "numeric_kind"] == "flag"
    assert frame.loc["sl/isAHRequired", "numeric_kind"] == "integer"
    assert frame.loc["x/Gain", "numeric_kind"] == "float"
    assert frame.loc["x/Gain", "number"] == 2.5


@pytest.mark.skipif(not DATA.exists(), reason="sample DAP file is not present")
def test_sample_file():
    frame = build_frame(read_dap(DATA))
    assert len(frame) == 49666
    assert frame["key"].is_unique
    assert frame["category"].notna().all()
    assert set(frame["category"]) <= {str(c) for c in Category}
