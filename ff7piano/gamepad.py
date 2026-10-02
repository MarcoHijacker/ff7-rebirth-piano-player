"""Thin wrapper around vgamepad's virtual DualShock 4."""
from __future__ import annotations

from .sheet import DIRECTIONS

VIGEM_URL = "https://github.com/nefarius/ViGEmBus/releases"


class GamepadError(RuntimeError):
    pass


def _explain(error: Exception) -> str:
    msg = str(error)
    if "BUS_NOT_FOUND" in msg:
        return (
            "The ViGEmBus driver is not installed (or the PC needs a restart after installing it).\n"
            f"Download it from {VIGEM_URL}, install it and restart."
        )
    if "BUS_VERSION_MISMATCH" in msg:
        return f"The installed ViGEmBus driver version is not compatible. Install another release from {VIGEM_URL}."
    return f"Could not create the virtual controller: {msg}"


class VirtualPad:
    """A virtual DS4 exposing just what the piano minigame needs."""

    def __init__(self) -> None:
        try:
            import vgamepad as vg  # connects to ViGEmBus at import time
        except Exception as e:
            raise GamepadError(_explain(e)) from None
        try:
            self._pad = vg.VDS4Gamepad()
        except Exception as e:
            raise GamepadError(_explain(e)) from None
        self._cross = vg.DS4_BUTTONS.DS4_BUTTON_CROSS

    def press_cross(self) -> None:
        self._pad.press_button(button=self._cross)
        self._pad.update()

    def release_cross(self) -> None:
        self._pad.release_button(button=self._cross)
        self._pad.update()

    def set_sticks(self, left: str | None = None, right: str | None = None) -> None:
        """Tilt the given stick(s) fully in a direction; None leaves a stick untouched."""
        if left is not None:
            x, y = DIRECTIONS[left]
            self._pad.left_joystick_float(x_value_float=x, y_value_float=y)
        if right is not None:
            x, y = DIRECTIONS[right]
            self._pad.right_joystick_float(x_value_float=x, y_value_float=y)
        self._pad.update()

    def release_sticks(self) -> None:
        self._pad.left_joystick_float(x_value_float=0.0, y_value_float=0.0)
        self._pad.right_joystick_float(x_value_float=0.0, y_value_float=0.0)
        self._pad.update()
