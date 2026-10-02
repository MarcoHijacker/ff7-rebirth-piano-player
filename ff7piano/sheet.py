"""Song sheets: loading, validation and writing.

A sheet is a YAML file describing every input of a song. Each event stores
its absolute time, so editing one note never shifts the rest of the song.

Example::

    title: One-Winged Angel
    notes: 310          # total shown on the results screen
    speed: 3            # note speed to set in the game (1-5)
    offset: 0.0         # shifts the whole song, in seconds (+ = later)
    events:
      - {n: 1, t: 14.3113, R: E}
      - {n: [2, 3], t: 14.7787, L: SE, R: SE}
      - {n: 4, t: 15.2347, L: N, shift: 0.05}

Event keys:
    n      Note number as counted by the game (a list of two numbers for a
           two-handed event, which the game counts as two notes).
    t      Time in seconds, measured from the moment the start button is
           released.
    L / R  Direction for the left / right stick: N, NE, E, SE, S, SW, W, NW.
    shift  Optional manual correction for this event only, in seconds.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable

import yaml

DIRECTIONS = {
    "N": (0.0, -1.0),
    "NE": (1.0, -1.0),
    "E": (1.0, 0.0),
    "SE": (1.0, 1.0),
    "S": (0.0, 1.0),
    "SW": (-1.0, 1.0),
    "W": (-1.0, 0.0),
    "NW": (-1.0, -1.0),
}

SHEET_EXTENSIONS = (".yaml", ".yml")


class SheetError(ValueError):
    """Raised when a sheet file is malformed. The message lists every problem."""


@dataclass
class Event:
    numbers: tuple[int, ...]
    time: float
    left: str | None = None
    right: str | None = None
    shift: float = 0.0

    @property
    def label(self) -> str:
        """Human-readable note number(s), e.g. '#147' or '#148-149'."""
        if len(self.numbers) == 1:
            return f"#{self.numbers[0]}"
        return f"#{self.numbers[0]}-{self.numbers[-1]}"

    @property
    def keys(self) -> str:
        """Human-readable inputs, e.g. 'R:W' or 'L:SE R:SE'."""
        parts = []
        if self.left:
            parts.append(f"L:{self.left}")
        if self.right:
            parts.append(f"R:{self.right}")
        return " ".join(parts)


@dataclass
class Sheet:
    title: str
    events: list[Event]
    notes: int
    speed: int = 3
    offset: float = 0.0
    source: str = ""
    path: str | None = field(default=None, compare=False)

    @property
    def duration(self) -> float:
        return self.events[-1].time if self.events else 0.0


# --------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------

def _as_numbers(value) -> tuple[int, ...]:
    if isinstance(value, bool):
        raise TypeError
    if isinstance(value, int):
        return (value,)
    if isinstance(value, (list, tuple)) and value and all(
        isinstance(v, int) and not isinstance(v, bool) for v in value
    ):
        return tuple(value)
    raise TypeError


def parse_sheet(data: dict, path: str | None = None) -> Sheet:
    """Build a Sheet from parsed YAML, collecting *all* problems at once."""
    errors: list[str] = []
    if not isinstance(data, dict):
        raise SheetError("the file must contain a YAML mapping (title, notes, events...)")

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("'title' is missing")
        title = os.path.splitext(os.path.basename(path or "untitled"))[0]

    def number(key, default, kind=float):
        value = data.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"'{key}' must be a number")
            return default
        return kind(value)

    offset = number("offset", 0.0)
    speed = number("speed", 3, int)
    declared = data.get("notes")

    raw_events = data.get("events")
    events: list[Event] = []
    if not isinstance(raw_events, list) or not raw_events:
        errors.append("'events' must be a non-empty list")
        raw_events = []

    expected_n = 1
    prev_time = None
    for i, raw in enumerate(raw_events, start=1):
        where = f"event {i}"
        if not isinstance(raw, dict):
            errors.append(f"{where}: must be a mapping like {{n: 1, t: 1.5, R: E}}")
            continue
        unknown = set(raw) - {"n", "t", "L", "R", "shift"}
        if unknown:
            errors.append(f"{where}: unknown key(s) {sorted(unknown)}")

        try:
            numbers = _as_numbers(raw.get("n"))
        except TypeError:
            errors.append(f"{where}: 'n' must be a note number or a list of two numbers")
            numbers = (expected_n,)
        where = f"event {i} (note {'-'.join(map(str, numbers))})"

        left, right = raw.get("L"), raw.get("R")
        for hand, value in (("L", left), ("R", right)):
            if value is not None and value not in DIRECTIONS:
                errors.append(f"{where}: {hand} direction {value!r} is not one of {', '.join(DIRECTIONS)}")
        if left is None and right is None:
            errors.append(f"{where}: needs at least one of L or R")

        hands = (left is not None) + (right is not None)
        if len(numbers) != hands:
            errors.append(f"{where}: {hands} stick(s) used but {len(numbers)} note number(s) given")
        if numbers[0] != expected_n or any(b != a + 1 for a, b in zip(numbers, numbers[1:])):
            errors.append(f"{where}: note numbers should continue from #{expected_n}")
        expected_n = numbers[-1] + 1

        t = raw.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)):
            errors.append(f"{where}: 't' must be a time in seconds")
            t = prev_time or 0.0
        elif prev_time is not None and t <= prev_time:
            errors.append(f"{where}: time {t} is not after the previous event ({prev_time})")
        prev_time = float(t)

        shift = raw.get("shift", 0.0)
        if isinstance(shift, bool) or not isinstance(shift, (int, float)):
            errors.append(f"{where}: 'shift' must be a number of seconds")
            shift = 0.0

        events.append(Event(numbers, float(t), left, right, float(shift)))

    counted = expected_n - 1
    if declared is None:
        declared = counted
    elif isinstance(declared, bool) or not isinstance(declared, int):
        errors.append("'notes' must be an integer")
        declared = counted
    elif events and declared != counted:
        errors.append(f"'notes' says {declared} but the events contain {counted} notes")

    if errors:
        raise SheetError("\n".join(errors))
    return Sheet(
        title=title.strip(),
        events=events,
        notes=declared,
        speed=speed,
        offset=offset,
        source=str(data.get("source", "")),
        path=path,
    )


def load_sheet(path: str) -> Sheet:
    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SheetError(f"not valid YAML: {e}") from None
    return parse_sheet(data, path)


def find_sheets(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith(SHEET_EXTENSIONS)
    )


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

def slugify(title: str) -> str:
    title = title.lower().replace("'", "").replace("\u2019", "")
    return re.sub(r"[^a-z0-9]+", "_", title).strip("_") or "song"


def _yaml_str(text: str) -> str:
    # json-style quoting is valid YAML and handles apostrophes, colons, etc.
    import json
    return json.dumps(text, ensure_ascii=False)


def dump_sheet(sheet: Sheet, header_comment: str | None = None) -> str:
    """Serialise a sheet with one event per line, aligned for easy editing."""
    lines = []
    if header_comment:
        lines += [f"# {line}".rstrip() for line in header_comment.splitlines()]
    lines += [
        f"title: {_yaml_str(sheet.title)}",
        f"notes: {sheet.notes}".ljust(16) + "# total shown on the results screen",
        f"speed: {sheet.speed}".ljust(16) + "# note speed to set in the game (1-5)",
        f"offset: {sheet.offset:g}".ljust(16) + "# shifts the whole song in seconds (+ = later)",
    ]
    if sheet.source:
        lines.append(f"source: {_yaml_str(sheet.source)}")
    lines.append("events:")
    for e in sheet.events:
        n = str(e.numbers[0]) if len(e.numbers) == 1 else f"[{', '.join(map(str, e.numbers))}]"
        parts = [f"n: {n},".ljust(15), f"t: {e.time:.4f},".ljust(13)]
        keys = []
        if e.left:
            keys.append(f"L: {e.left}")
        if e.right:
            keys.append(f"R: {e.right}")
        if e.shift:
            keys.append(f"shift: {e.shift:+.3f}")
        lines.append("  - {" + " ".join(parts) + ", ".join(keys) + "}")
    return "\n".join(lines) + "\n"


def number_events(raw: Iterable[tuple[float, str | None, str | None]]) -> list[Event]:
    """Turn (time, left, right) tuples into numbered events."""
    events, n = [], 1
    for t, left, right in raw:
        count = (left is not None) + (right is not None)
        events.append(Event(tuple(range(n, n + count)), t, left, right))
        n += count
    return events
