"""Plays a sheet on the virtual controller with precise timing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import timing
from .sheet import Event, Sheet

# How long the start button is held before the song clock starts.
START_PRESS = 0.1


@dataclass
class Settings:
    # Every event is sent this many seconds early, to compensate for the
    # input latency of the chiaki-ng stream. Raise it if notes land late,
    # lower it (or make it negative) if they land early.
    lead: float = 0.08
    # How long a stick is held in a direction.
    hold: float = 0.10
    # An event sent this much later than planned is reported as late.
    late_warning: float = 0.015


@dataclass
class Report:
    played: int = 0
    total: int = 0
    aborted: bool = False
    late: list[tuple[Event, float]] = field(default_factory=list)


def hold_time(settings: Settings, gap: float | None) -> float:
    """Hold duration for an event followed by the next one `gap` seconds later.

    On fast passages the stick is released early enough to leave a neutral
    gap of at least ~40% of the interval, so the game sees two separate inputs.
    """
    if gap is None or gap <= 0:
        return settings.hold
    return max(0.03, min(settings.hold, gap * 0.6))


def play(
    sheet: Sheet,
    pad,
    settings: Settings,
    on_event: Callable[[Event, float, float], None] | None = None,
) -> Report:
    """Start the song with the cross button, then play every event on time.

    `on_event(event, song_time, lateness)` is called right after each event
    is sent. Ctrl+C stops the song; the sticks are always released.
    """
    report = Report(total=sheet.notes)
    targets = [sheet.offset + e.time + e.shift - settings.lead for e in sheet.events]

    try:
        pad.press_cross()
        timing.sleep_until(timing.now() + START_PRESS)
        pad.release_cross()
        start = timing.now()

        for i, event in enumerate(sheet.events):
            target = start + targets[i]
            timing.sleep_until(target)
            sent = timing.now()
            pad.set_sticks(event.left, event.right)

            lateness = sent - target
            if lateness > settings.late_warning:
                report.late.append((event, lateness))
            report.played = event.numbers[-1]
            if on_event:
                on_event(event, sent - start, lateness)

            gap = targets[i + 1] - targets[i] if i + 1 < len(targets) else None
            timing.sleep_until(sent + hold_time(settings, gap))
            pad.release_sticks()
    except KeyboardInterrupt:
        report.aborted = True
    finally:
        pad.release_sticks()
    return report
