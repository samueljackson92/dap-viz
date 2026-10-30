from dap_viz.parser import parse_lines, pulse_number


def test_simple_and_empty_values():
    records = parse_lines(["l1/PulseNumber 103169\n", "sl/RFReply \n", "l1/Blank  \n"])
    assert [(r.key, r.value) for r in records] == [
        ("l1/PulseNumber", "103169"),
        ("sl/RFReply", ""),
        ("l1/Blank", " "),
    ]


def test_continuation_lines():
    lines = [
        "mc/PtypeDesc Seeded, V37 - 2.5MA/2.8 T\\\n",
        "neon seeded pulse ~28 MW\n",
        "ScIn/BdownPtypeDesc 15kA premag\n",
    ]
    records = parse_lines(lines)
    assert len(records) == 2
    assert records[0].value == "Seeded, V37 - 2.5MA/2.8 T\nneon seeded pulse ~28 MW"
    assert records[1].line == 3


def test_last_line_continues():
    records = parse_lines(["a/b one\\\n"])
    assert records[0].value == "one"


def test_pulse_number():
    assert pulse_number("data/DAP-0103169.txt") == 103169
    assert pulse_number("notes.txt") is None
