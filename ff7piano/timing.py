"""High-precision waiting on Windows (and anywhere else)."""
from __future__ import annotations

import atexit
import sys
from time import perf_counter, sleep

# The last part of every wait is a busy-wait instead of sleep(): sleep() can
# overshoot by several milliseconds, busy-waiting is exact.
SPIN_WINDOW = 0.003

_configured = False


def configure_system_timing() -> list[str]:
    """Make timing as stable as possible. Returns warnings (empty if all good).

    - timeBeginPeriod(1): system timer at 1 ms instead of the default
      ~15.6 ms, so sleep() wakes up on time.
    - HIGH_PRIORITY_CLASS: other programs (browser, stream decoding,
      antivirus) are less likely to steal the CPU right when a note is due.
    - SetThreadExecutionState: keeps the PC from sleeping mid-song.
    """
    global _configured
    if _configured or sys.platform != "win32":
        return []
    _configured = True
    warnings = []
    try:
        import ctypes

        winmm = ctypes.WinDLL("winmm")
        winmm.timeBeginPeriod(1)
        atexit.register(winmm.timeEndPeriod, 1)

        kernel32 = ctypes.WinDLL("kernel32")
        high_priority_class = 0x00000080
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), high_priority_class)
        es_continuous, es_system_required = 0x80000000, 0x00000001
        kernel32.SetThreadExecutionState(es_continuous | es_system_required)
    except Exception as e:  # pragma: no cover - Windows only
        warnings.append(f"could not tune Windows timers: {e}")
    return warnings


def sleep_until(target: float) -> None:
    """Wait until an absolute perf_counter() timestamp.

    Sleeps for most of the interval, then busy-waits the last few ms.
    Waiting for absolute targets means jitter never accumulates.
    """
    remaining = target - perf_counter()
    if remaining > SPIN_WINDOW:
        sleep(remaining - SPIN_WINDOW)
    while perf_counter() < target:
        pass


now = perf_counter
