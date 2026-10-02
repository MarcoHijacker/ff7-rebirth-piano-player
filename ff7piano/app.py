"""Interactive command-line front end."""
from __future__ import annotations

import os
import sys
from time import sleep

import yaml

from . import __version__, timing
from .gamepad import GamepadError, VirtualPad
from .player import Settings, play
from .sheet import Sheet, SheetError, find_sheets, load_sheet

SETTINGS_FILE = "settings.yaml"


def base_dir() -> str:
    """Folder containing the exe (frozen build) or the project root (source)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# Settings persistence
# --------------------------------------------------------------------------

def load_settings(folder: str) -> Settings:
    settings = Settings()
    path = os.path.join(folder, SETTINGS_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for key in ("lead", "hold"):
            if isinstance(data.get(key), (int, float)) and not isinstance(data.get(key), bool):
                setattr(settings, key, float(data[key]))
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"(Ignoring {SETTINGS_FILE}: {e})")
    return settings


def save_settings(folder: str, settings: Settings) -> None:
    path = os.path.join(folder, SETTINGS_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "# Saved by ff7piano. lead: seconds each note is sent early to\n"
                "# compensate for streaming latency. hold: seconds a stick is held.\n"
                f"lead: {settings.lead:g}\nhold: {settings.hold:g}\n"
            )
    except OSError as e:
        print(f"(Could not save {SETTINGS_FILE}: {e})")


# --------------------------------------------------------------------------
# Menu
# --------------------------------------------------------------------------

def load_library(songs_dir: str) -> tuple[list[Sheet], list[tuple[str, str]]]:
    """Load every sheet; broken files are reported instead of stopping the app."""
    sheets, broken = [], []
    for path in find_sheets(songs_dir):
        try:
            sheets.append(load_sheet(path))
        except SheetError as e:
            broken.append((os.path.basename(path), str(e)))
    sheets.sort(key=lambda s: s.title.lower())
    return sheets, broken


def print_menu(sheets: list[Sheet], broken, settings: Settings) -> None:
    print()
    print("=" * 60)
    print(f" FF7 Rebirth Piano  v{__version__}")
    print("=" * 60)
    width = max((len(s.title) for s in sheets), default=10)
    for i, s in enumerate(sheets, start=1):
        print(f" {i:>2}. {s.title:<{width}}   {s.notes:>3} notes   {s.duration / 60:4.1f} min")
    for name, error in broken:
        first = error.splitlines()[0]
        extra = len(error.splitlines()) - 1
        more = f" (+{extra} more)" if extra else ""
        print(f"  !  {name}: {first}{more}  -> type 'check' for details")
    print("-" * 60)
    print(f" Lead: {settings.lead:+.3f} s   Hold: {settings.hold:.3f} s")
    print(" [number] play   o = change lead   check = show sheet errors   q = quit")


def ask_float(prompt: str, current: float) -> float:
    raw = input(f"{prompt} [{current:g}]: ").strip().replace(",", ".")
    if not raw:
        return current
    try:
        return float(raw)
    except ValueError:
        print("Not a number, keeping the current value.")
        return current


def wait_for_click() -> None:
    """Block until the user clicks (on the chiaki-ng window).

    The listener is fully stopped before the song starts: running the song
    inside the click callback would keep a Windows low-level mouse hook
    blocked for the whole song, which lags the mouse system-wide and
    disturbs the timing.
    """
    from pynput.mouse import Listener

    def on_click(x, y, button, pressed):
        if pressed:
            return False  # stops the listener

    with Listener(on_click=on_click) as listener:
        listener.join()
    sleep(0.2)  # let the click's release event pass before the song starts


def run_song(sheet: Sheet, pad: VirtualPad, settings: Settings) -> None:
    print()
    print(f"{sheet.title}: {sheet.notes} notes. Make sure the song is highlighted in the")
    print(f"game menu and note speed is {sheet.speed}/5.")
    print("Click on the chiaki-ng window to start. Ctrl+C stops the song.")
    try:
        wait_for_click()
    except KeyboardInterrupt:
        print("Cancelled.")
        return

    def on_event(event, song_time, lateness):
        late = f"   <-- LATE by {lateness * 1000:.0f} ms" if lateness > settings.late_warning else ""
        print(f"  {event.label:<9} {event.keys:<12} t={event.time + event.shift:8.3f}{late}")

    report = play(sheet, pad, settings, on_event)
    print()
    if report.aborted:
        print(f"Stopped at note {report.played}/{report.total}.")
    else:
        print(f"Finished: {report.total} notes sent.")
    if report.late:
        worst_event, worst = max(report.late, key=lambda x: x[1])
        print(f"{len(report.late)} event(s) were sent late; worst: {worst_event.label} ({worst * 1000:.0f} ms).")
        print("Many late events mean the PC was busy: close other programs and plug in the charger.")
    elif not report.aborted:
        print("Every event was sent on time. If the game keeps missing the same note,")
        print("adjust that note's 't' (or add a 'shift') in the sheet: it is listed by number above.")


def main() -> int:
    folder = base_dir()
    songs_dir = os.path.join(folder, "songs")
    for warning in timing.configure_system_timing():
        print(f"(Warning: {warning})")

    try:
        pad = VirtualPad()
    except GamepadError as e:
        print(f"\n{e}")
        input("\nPress Enter to exit...")
        return 1

    settings = load_settings(folder)
    while True:
        sheets, broken = load_library(songs_dir)  # re-read: edits apply without restarting
        if not sheets and not broken:
            print(f"\nNo sheets found in {songs_dir}")
        print_menu(sheets, broken, settings)
        try:
            choice = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return 0

        if choice in ("q", "quit", "exit"):
            return 0
        if choice == "o":
            settings.lead = ask_float("Lead in seconds", settings.lead)
            save_settings(folder, settings)
            continue
        if choice == "check":
            if not broken:
                print("All sheets are valid.")
            for name, error in broken:
                print(f"\n{name}:")
                for line in error.splitlines():
                    print(f"  - {line}")
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(sheets):
            run_song(sheets[int(choice) - 1], pad, settings)
            continue
        # Also accept a (partial) song title
        matches = [s for s in sheets if choice and choice in s.title.lower()]
        if len(matches) == 1:
            run_song(matches[0], pad, settings)
        else:
            print("Unknown choice." if not matches else "More than one song matches, use the number.")
