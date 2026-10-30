import pytest

from dap_viz.classify import (
    Category,
    classify_value,
    flatten_config,
    is_categorical,
    parse_config_block,
    parse_dsl_waveform,
    parse_timer,
    parse_typed_list,
)

NB_POWER = (
    "pm/powerWave ppower>NB @ 15 0.0 0.0 49 0 49.001 12 49.201 12 49.202 16 "
    "49.502 16 50.002 27.5 56.002 27.5 56.003 18 57.203 18 57.204 10 57.604 10 "
    "57.605 6 58.205 6 58.206 0"
)


@pytest.mark.parametrize(
    ("value", "category"),
    [
        ("103169", Category.NUMERIC),
        ("-999.999", Category.NUMERIC),
        ("2.5E3", Category.NUMERIC),
        ("", Category.EMPTY),
        ("  ", Category.EMPTY),
        ("**** mread: un-initialised value", Category.ERROR),
        ("3   1 1   2 2   3.3 4.4", Category.NUMERIC_ARRAY),
        ("0x601b64bc", Category.HEX),
        ("30/09/2020", Category.DATETIME),
        ("Wed Jun 21 12:54:06 2023", Category.DATETIME),
        ("2013-11-28", Category.DATETIME),
        (NB_POWER, Category.DSL_WAVEFORM),
        ("pf/Z0p$Scenario   PC-Z0P @ 2 0 0 0.01 0.3", Category.DSL_WAVEFORM),
        (
            "KG1C/CLK: npts=64000 I(21@1.000000) P(17000@1.0000E-03)",
            Category.DSL_TIMER,
        ),
        ("/jet/pm/PIW/KL1-P4DA/Beta/restart2-v1.1.txt", Category.FILEPATH),
        ("ComparatorGAM-v1.5.cfg", Category.FILEPATH),
        ("PF/I0P&25-46<55:432", Category.WAVEFORM_REF),
        ("pf/d3ps-ss1:401", Category.WAVEFORM_REF),
        ("pf/CPS/c1_ther/a1", Category.SIGNAL_PATH),
        ("PhysicalTile = { 1 = IWGL_3X11 }", Category.DSL_CONFIG),
        ("Material = Be\nOctant = 8", Category.DSL_CONFIG),
        ('I 0 C "None" I 0 R 0.0 R 0.0', Category.DSL_TYPED_LIST),
        ("R 100.0 R 100.0 R 100.0 R 100.0", Category.DSL_TYPED_LIST),
        ("Hongjuan Sun", Category.TEXT),
        ("Be", Category.TEXT),
    ],
)
def test_classify_value(value, category):
    assert classify_value(value) == category


def test_is_categorical():
    assert is_categorical("Be", value_count=252, family_size=1, family_distinct=1)
    assert is_categorical("x", value_count=1, family_size=10, family_distinct=2)
    assert not is_categorical(
        "unique", value_count=1, family_size=10, family_distinct=10
    )
    assert not is_categorical("a\nb", value_count=9, family_size=9, family_distinct=1)


def test_parse_dsl_waveform():
    wave = parse_dsl_waveform(NB_POWER)
    assert wave is not None
    assert wave.name == "pm/powerWave"
    assert wave.target == "ppower>NB"
    assert len(wave.times) == 15
    assert wave.values[6] == 27.5
    assert wave.times[-1] == 58.206


def test_parse_dsl_waveform_comment():
    wave = parse_dsl_waveform(
        "PM/Launcher$Power LUPOWR> @ 2 0 0 19.9 0  Computed by V2"
    )
    assert wave is not None
    assert wave.comment == "Computed by V2"


def test_parse_dsl_waveform_bad():
    assert parse_dsl_waveform("no at sign") is None
    assert parse_dsl_waveform("a b @ 3 1 2") is None


def test_parse_timer():
    clock, npts, segments = parse_timer(
        "KG1C/CLK: npts=64000 I(21@1.0) P(17000@1.0E-03)"
    )
    assert clock == "KG1C/CLK"
    assert npts == 64000
    assert [(s.kind, s.count, s.dt) for s in segments] == [
        ("I", 21, 1.0),
        ("P", 17000, 0.001),
    ]


def test_parse_typed_list():
    items = parse_typed_list('I 0 C "None" R 2.5')
    assert [(i.kind, i.value) for i in items] == [("I", 0.0), ("C", "None"), ("R", 2.5)]


def test_parse_config_block_nested():
    text = (
        "Class = PiwStopResponse\nValidation = {\n"
        "    1 = {EnsureReferencedStopsAndScenariosNotObsolete}\n}\n"
        'P4GapControlMode = 321\nDescription = "Fast stop"'
    )
    flat = flatten_config(parse_config_block(text))
    assert flat == {
        "Class": "PiwStopResponse",
        "Validation.1": "EnsureReferencedStopsAndScenariosNotObsolete",
        "P4GapControlMode": "321",
        "Description": "Fast stop",
    }


def test_parse_config_block_inline():
    flat = flatten_config(parse_config_block("PhysicalTile = { 1 = A 2 = B }"))
    assert flat == {"PhysicalTile.1": "A", "PhysicalTile.2": "B"}
