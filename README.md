# FF7 Rebirth Piano Player

Plays the piano minigame of **Final Fantasy VII Rebirth** for you, with perfect timing.

The program creates a virtual DualShock 4 controller on your Windows PC and plays every note of a song through [**chiaki-ng**](https://github.com/streetpea/chiaki-ng), the open source PS5 streaming client, following a *sheet* that describes when to tilt each stick and in which direction.

> Unofficial fan project, not affiliated with Square Enix or Sony. Use at your own risk.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Playing a song](#playing-a-song)
- [Using the program](#using-the-program)
- [Fixing a song that misses notes](#fixing-a-song-that-misses-notes)
- [Troubleshooting](#troubleshooting)
- [Included songs](#included-songs)
- [Sheet format](#sheet-format)
- [Development](#development)
- [Project structure](#project-structure)
- [Credits](#credits)
- [License](#license)

---

## Features

- **Accurate timing.** Events are scheduled on absolute timestamps with a 1 ms system timer, a busy-wait for the last milliseconds and high process priority. Delays never accumulate.
- **Song menu.** After a song ends you are back at the menu, so you can play the next one without restarting. Sheets are re-read every time, so edits apply immediately.
- **Numbered notes.** Every note is numbered the way the game counts it (a two-handed note counts as two), and the log shows the number of every event, so you know exactly which note to fix.
- **Readable sheet format.** YAML with one line per event and absolute times: changing one note never shifts the rest of the song.
- **Sheet validation.** Malformed sheets are reported with every problem and its note number, instead of stopping the song halfway.

## Requirements

| What | Notes |
|---|---|
| Windows 10 / 11 | The virtual controller only exists on Windows. |
| [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases) | Creates the virtual controller. Version **1.17.333** is recommended (see [Troubleshooting](#troubleshooting)). Install it and restart the PC. |
| [**chiaki-ng**](https://github.com/streetpea/chiaki-ng/releases) | The PS5 streaming client the program is tested with. The official **PS Remote Play app is not supported**: it closes as soon as it detects the ViGEmBus virtual controller driver. |
| A stable connection | Wired PS5 and PC work best. A low stream resolution (e.g. 720p) reduces latency. |

## Installation

First install the **ViGEmBus** driver (see [Requirements](#requirements)) and restart the PC. Then choose one of the options below.

### Option A: download the ready-made exe

1. Download `ff7_piano-windows.zip` from the [Releases page](https://github.com/MarcoHijacker/ff7-rebirth-piano-player/releases/latest).
2. Unzip it anywhere. Keep the `songs` folder next to `ff7_piano.exe`.

> Windows SmartScreen may warn that the exe is not recognised, because it is not signed. Choose *More info → Run anyway*, or build it yourself with option B.

### Option B: build the exe yourself

You need [Python 3.10+](https://www.python.org/downloads/) (tick *Add python.exe to PATH* while installing) and [Git](https://git-scm.com/download/win). In PowerShell:

```
git clone https://github.com/MarcoHijacker/ff7-rebirth-piano-player.git
cd ff7-rebirth-piano-player
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --name ff7_piano --collect-data vgamepad ff7_piano.py
Copy-Item songs dist\songs -Recurse
```

The program is now in the `dist` folder: `ff7_piano.exe` with its `songs` folder next to it. You can move `dist` anywhere and rename it.

- If PowerShell refuses to activate the environment, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once and try again.
- Installing `vgamepad` opens the ViGEmBus installer if the driver is missing: accept it (it is version 1.17.333, the recommended one), or cancel it if the driver is already installed.
- `--collect-data vgamepad` is required: it bundles the `ViGEmClient.dll` that `vgamepad` loads at runtime.

### Option C: run from source

Same as option B, but instead of building the exe install only the runtime dependencies and start the script:

```
python -m pip install -r requirements.txt
python ff7_piano.py
```

(`python -m ff7piano` works too.)

## Playing a song

1. Start **chiaki-ng** and connect to your PS5.
2. In the game, go to the piano, **highlight the song** you want to play and set **note speed to 3/5**. Don't start it.
3. Run `ff7_piano.exe` (or `python ff7_piano.py`), type the number of the song and press Enter.
4. **Click on the chiaki-ng window.** The program presses ✕ to start the song and plays it.
5. When the song ends you are back at the menu: highlight the next song in the game and pick it.

## Using the program

```
============================================================
 FF7 Rebirth Piano  v2.0.0
============================================================
  1. Aerith's Theme             142 notes    2.2 min
  2. Aerith's Theme (Quest)     142 notes    2.3 min
  ...
  9. Two Legs? Nothin' To It    205 notes    2.2 min
------------------------------------------------------------
 Lead: +0.080 s   Hold: 0.100 s
 [number] play   o = change lead   check = show sheet errors   q = quit
>
```

| Command | Action |
|---|---|
| `1`, `2`, ... | Play that song. Part of a title (e.g. `angel`) also works. |
| `o` | Change the **lead**, i.e. how early every event is sent to compensate for streaming latency. The value is saved in `settings.yaml`. |
| `check` | Show every problem found in sheets that could not be loaded. |
| `q` | Quit. |

While a song is playing, every event is logged with its note number:

```
  #145      R:N          t=  67.078
  #146      R:W          t=  67.587
  #147      R:W          t=  68.106
  #148-149  L:SE R:SE    t=  69.223   <-- LATE by 21 ms
```

**Ctrl+C** stops the song and goes back to the menu. At the end you get a summary: if any event was sent late, the PC was busy at that moment (close other programs, plug in the charger).

## Fixing a song that misses notes

First look at the in-game counter (Excellent / Good / Bad / Miss).

- **Every note is slightly early or late**: change the lead with `o` in the menu. Raise it if notes land late, lower it (even below zero) if they land early. Try steps of 0.02 s.
- **The whole song is shifted by the same amount**: set `offset` at the top of that song's sheet.
- **The same note fails every time**: find its number (the game counter and the log use the same numbering), open the sheet in any text editor and adjust that event. Either change its `t`, or add a `shift` to keep the original value visible:

  ```yaml
  - {n: 147,         t: 68.1060,   R: W, shift: +0.050}
  ```

  Only that event moves, the rest of the song is untouched. Save the file and play again: there is no need to restart the program.

## Troubleshooting

| Problem | Solution |
|---|---|
| `The ViGEmBus driver is not installed` | Install [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) and restart the PC. |
| PS Remote Play closes right after connecting | Expected: the official app closes as soon as it detects the ViGEmBus driver. Use [chiaki-ng](https://github.com/streetpea/chiaki-ng/releases) instead. |
| Problems after installing several ViGEmBus versions | Keep only one: uninstall every *ViGEm* / *Nefarius* entry in Settings → Apps, restart and install [ViGEmBus 1.17.333](https://github.com/ViGEm/ViGEmBus/releases/tag/setup-v1.17.333). Installing `vgamepad` with pip also launches that installer. |
| Many `LATE` warnings, rhythm drifting | The PC is overloaded: close browsers, screen recorders and other heavy programs, and plug in the charger. Screen recording while playing is not recommended on slow PCs. |
| The song starts but nothing happens | The click must be on the chiaki-ng window, and the song must be highlighted (not started) in the game menu. |
| Notes are early or late | See [Fixing a song that misses notes](#fixing-a-song-that-misses-notes). |
| A song is missing from the menu or shows `!` | The sheet is malformed: type `check` to see every problem, with the note number. |

## Included songs

| Song | Notes | Sheet |
|---|---:|---|
| On Our Way | 148 | from S-rank video |
| Tifa's Theme | 146 | from S-rank video |
| Barret's Theme | 109 | from S-rank video |
| Cinco de Chocobo | 145 | from S-rank video |
| Two Legs? Nothin' To It | 205 | from S-rank video |
| Aerith's Theme | 142 | from S-rank video |
| Aerith's Theme (Quest) | 142 | same notes as Aerith's Theme, starting 6.62 s later |
| Let the Battles Begin! | 256 | verified in game |
| One-Winged Angel | 310 | verified in game |

Every sheet was timed on an S-rank gameplay video, and its note count matches the game.

## Sheet format

Sheets live in the `songs` folder, one YAML file per song. Any text editor works.

```yaml
title: "One-Winged Angel"
notes: 310      # total shown on the results screen
speed: 3        # note speed to set in the game (1-5)
offset: 0       # shifts the whole song in seconds (+ = later)
source: "timed on an S-rank gameplay video, verified in game (perfect score)"
events:
  - {n: 1,           t: 14.3113,   R: E}
  - {n: 2,           t: 14.7787,   R: E}
  - {n: [16, 17],    t: 20.9543,   L: NE, R: SW}
  - {n: 18,          t: 21.4390,   L: N, shift: +0.030}
```

| Key | Meaning |
|---|---|
| `title` | Name shown in the menu (use the in-game name). |
| `notes` | Total number of notes; must match the events. |
| `speed` | Note speed to set in the game (1-5). |
| `offset` | Optional. Seconds added to every event. |
| `source` | Optional. Where the sheet comes from. |
| `events` | One entry per input, in time order. |

Each event:

| Key | Meaning |
|---|---|
| `n` | Note number as counted by the game. A two-handed event counts as two notes and has two numbers: `[16, 17]`. |
| `t` | Time in seconds, measured from the moment the ✕ button that starts the song is released. |
| `L`, `R` | Direction for the left / right stick: `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`. At least one is required; both for a two-handed note. |
| `shift` | Optional. Correction in seconds for this event only. |

Sheets are validated when loaded: note numbers must be consecutive, times increasing, directions valid and the total must match `notes`.

## Development

**Tests** (they also validate every sheet in `songs/`):

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

**Releases.** Pushing a `v*` tag (e.g. `git tag v2.0.0` then `git push origin v2.0.0`) builds the exe on GitHub and publishes `ff7_piano-windows.zip` on the Releases page (`.github/workflows/release.yml`). Every push also runs the tests (`.github/workflows/ci.yml`).

## Project structure

```
ff7_piano.py              entry point (also used by PyInstaller)
ff7piano/
  app.py                  menu, settings, song loop
  player.py               plays a sheet on the controller
  gamepad.py              virtual DualShock 4 (vgamepad)
  timing.py               precise waiting and Windows timer setup
  sheet.py                sheet format: loading, validation, writing
songs/                    one YAML sheet per song
tests/                    pytest suite
```

## Credits

This project is a rewrite of **[ff7_rebirth_piano](https://github.com/mbw8421/ff7_rebirth_piano)** by **[mbw8421](https://github.com/mbw8421)**, who had the original idea and wrote the first version of the script. Thank you!

Also thanks to:

- [@bad1dea](https://github.com/bad1dea), for most of the song sheets of the original project;
- [@KingAndaval](https://github.com/KingAndaval), for the [macOS fork](https://github.com/KingAndaval/ff7_rebirth_piano) of the original project;
- [vgamepad](https://github.com/yannbouteiller/vgamepad) and [ViGEmBus](https://github.com/nefarius/ViGEmBus), which make the virtual controller possible;
- [chiaki-ng](https://github.com/streetpea/chiaki-ng), the open source PlayStation Remote Play client.

## License

[MIT](LICENSE). The original project is also released under the MIT license; its copyright notice is kept in the license file.
