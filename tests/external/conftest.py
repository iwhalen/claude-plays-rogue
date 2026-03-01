"""Shared fixtures for rogomatic_llm.external tests."""

from __future__ import annotations

import pytest

from rogomatic_llm.external.screen import ScreenState


@pytest.fixture()
def empty_screen() -> ScreenState:
    return ScreenState.empty()


@pytest.fixture()
def screen_with_player() -> ScreenState:
    """A screen with the player at row 10, col 40."""
    s = ScreenState.empty()
    s.characters[10][40] = "@"
    return s


@pytest.fixture()
def rogue_status_line() -> str:
    """Typical Rogue 5.3+ status bar text."""
    return "Level: 3  Gold: 142  Hp: 10(12)  Str: 16(16)  Arm: 4  Exp: 2/27"


@pytest.fixture()
def screen_with_status(rogue_status_line: str) -> ScreenState:
    """A screen whose row 23 contains a valid status bar."""
    s = ScreenState.empty()
    for i, ch in enumerate(rogue_status_line):
        if i < ScreenState.COLS:
            s.characters[ScreenState.STATUS_ROW][i] = ch
    return s


@pytest.fixture()
def cursor_move_bytes() -> bytes:
    """ESC[5;20H  → move cursor to row 4, col 19 (0-based)."""
    return b"\x1b[5;20H"


@pytest.fixture()
def clear_screen_bytes() -> bytes:
    """Ctrl-L clear screen."""
    return b"\x0c"


@pytest.fixture()
def sample_rogue_frame() -> bytes:
    """A small VT100 byte sequence that draws part of a Rogue screen."""
    parts: list[bytes] = []
    parts.append(b"\x0c")  # clear screen
    parts.append(b"\x1b[2;1H")  # row 1, col 0
    parts.append(b"-----")
    parts.append(b"\x1b[1;1H")  # row 0, col 0
    parts.append(b"the hobbit hit you")
    parts.append(b"\x1b[11;41H")  # row 10, col 40
    parts.append(b"@")
    return b"".join(parts)
