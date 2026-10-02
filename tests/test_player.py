from ff7piano import timing
from ff7piano.player import Settings, hold_time, play
from ff7piano.sheet import parse_sheet


class FakePad:
    def __init__(self):
        self.log = []

    def press_cross(self):
        self.log.append(("cross", timing.now()))

    def release_cross(self):
        pass

    def set_sticks(self, left=None, right=None):
        self.log.append((left, right, timing.now()))

    def release_sticks(self):
        self.log.append(("release", timing.now()))


def test_events_are_sent_on_time():
    sheet = parse_sheet({
        "title": "t",
        "offset": 0.01,
        "events": [
            {"n": 1, "t": 0.05, "R": "E"},
            {"n": [2, 3], "t": 0.15, "L": "N", "R": "S"},
            {"n": 4, "t": 0.25, "L": "W", "shift": 0.02},
        ],
    })
    pad = FakePad()
    report = play(sheet, pad, Settings(lead=0.02, hold=0.03))
    start = pad.log[0][1] + 0.1  # clock starts when the cross button is released
    sent = [entry for entry in pad.log if entry[0] not in ("cross", "release")]
    expected = [0.05, 0.15, 0.27]
    for (left, right, t), e, want in zip(sent, sheet.events, expected):
        assert (left, right) == (e.left, e.right)
        assert abs((t - start) - (want + 0.01 - 0.02)) < 0.004
    assert report.played == 4 and not report.aborted


def test_hold_time_leaves_a_neutral_gap():
    s = Settings(hold=0.1)
    assert hold_time(s, None) == 0.1
    assert hold_time(s, 0.5) == 0.1
    assert abs(hold_time(s, 0.1) - 0.06) < 1e-9
    assert hold_time(s, 0.01) == 0.03
