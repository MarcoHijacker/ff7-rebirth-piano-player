import os

import pytest
import yaml

from ff7piano.sheet import Event, Sheet, SheetError, dump_sheet, find_sheets, load_sheet, number_events, parse_sheet, slugify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID = {
    "title": "Test Song",
    "notes": 4,
    "events": [
        {"n": 1, "t": 1.0, "R": "E"},
        {"n": [2, 3], "t": 1.5, "L": "SE", "R": "W"},
        {"n": 4, "t": 2.0, "L": "N", "shift": 0.05},
    ],
}


def test_parse_valid_sheet():
    sheet = parse_sheet(VALID)
    assert sheet.title == "Test Song"
    assert sheet.notes == 4
    assert [e.label for e in sheet.events] == ["#1", "#2-3", "#4"]
    assert sheet.events[1].keys == "L:SE R:W"
    assert sheet.events[2].shift == 0.05


def test_all_errors_are_reported_together():
    bad = {
        "title": "Bad",
        "notes": 9,
        "events": [
            {"n": 1, "t": 2.0, "R": "EE"},
            {"n": 3, "t": 1.0, "L": "N"},
            {"n": 4, "t": 3.0},
        ],
    }
    with pytest.raises(SheetError) as err:
        parse_sheet(bad)
    msg = str(err.value)
    assert "'EE'" in msg
    assert "continue from #2" in msg
    assert "not after the previous event" in msg
    assert "needs at least one of L or R" in msg
    assert "'notes' says 9" in msg


def test_double_needs_two_numbers():
    bad = {"title": "x", "events": [{"n": 1, "t": 1.0, "L": "N", "R": "S"}]}
    with pytest.raises(SheetError, match="2 stick"):
        parse_sheet(bad)


def test_dump_round_trip():
    sheet = parse_sheet(VALID)
    again = parse_sheet(yaml.safe_load(dump_sheet(sheet, "header")))
    assert again == sheet


def test_number_events():
    events = number_events([(1.0, None, "E"), (2.0, "N", "S"), (3.0, "W", None)])
    assert [e.numbers for e in events] == [(1,), (2, 3), (4,)]


def test_slugify():
    assert slugify("Aerith's Theme") == "aeriths_theme"
    assert slugify("Let the Battles Begin!") == "let_the_battles_begin"
    assert slugify("One-Winged Angel") == "one_winged_angel"


@pytest.mark.parametrize("path", find_sheets(os.path.join(ROOT, "songs")))
def test_bundled_sheets_are_valid(path):
    sheet = load_sheet(path)
    assert sheet.notes == sheet.events[-1].numbers[-1]
    assert os.path.basename(path) == slugify(sheet.title) + ".yaml"
