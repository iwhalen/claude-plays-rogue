"""Human player that relays terminal I/O to and from a Rogue game."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from io import StringIO
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cpr.player.base import Player

if TYPE_CHECKING:
    from cpr.external.game import RogueGame

_ESC = 0x1B

_ANSI_TO_ROGUE: dict[bytes, bytes] = {
    b"\x1b[A": b"k",  # Up
    b"\x1b[B": b"j",  # Down
    b"\x1b[C": b"l",  # Right
    b"\x1b[D": b"h",  # Left
    b"\x1bOA": b"k",  # Up    (application mode)
    b"\x1bOB": b"j",  # Down  (application mode)
    b"\x1bOC": b"l",  # Right (application mode)
    b"\x1bOD": b"h",  # Left  (application mode)
    b"\x1b[H": b"y",  # Home  (xterm)
    b"\x1b[F": b"b",  # End   (xterm)
    b"\x1bOH": b"y",  # Home  (application mode)
    b"\x1bOF": b"b",  # End   (application mode)
    b"\x1b[1~": b"y",  # Home  (vt220)
    b"\x1b[4~": b"b",  # End   (vt220)
    b"\x1b[5~": b"u",  # Page Up
    b"\x1b[6~": b"n",  # Page Down
}

_MAX_SEQ_LEN = max(len(s) for s in _ANSI_TO_ROGUE)


def _translate_keys(data: bytes) -> bytes:
    """Replace ANSI arrow/nav escape sequences with rogue vi-keys."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        if data[i] == _ESC and i + 1 < n:
            matched = False
            for length in range(min(_MAX_SEQ_LEN, n - i), 1, -1):
                seq = data[i : i + length]
                replacement = _ANSI_TO_ROGUE.get(seq)
                if replacement is not None:
                    out.extend(replacement)
                    i += length
                    matched = True
                    break
            if not matched:
                out.append(data[i])
                i += 1
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


_GAME_ROWS = 24
_GAME_COLS = 80
_GAME_PANEL_W = _GAME_COLS + 4
_GAME_PANEL_H = _GAME_ROWS + 2
_CONSOLE_W = _GAME_PANEL_W + 2

_HIDE_CURSOR = b"\x1b[?25l"
_SHOW_CURSOR = b"\x1b[?25h"
_HOME = b"\x1b[H"
_CLEAR = b"\x1b[2J"
_CLEAR_BELOW = b"\x1b[J"


def _render_frame(
    console: Console,
    buf: StringIO,
    screen_chars: list[list[str]],
) -> bytes:
    """Render the game screen as a rich panel formatted for a raw-mode terminal.

    Newlines are converted to \\r\\n for raw-mode compatibility.
    """
    game_content = "\n".join("".join(row) for row in screen_chars)
    game_panel = Panel(
        Text(game_content, no_wrap=True, overflow="crop"),
        title="[bold yellow]Rogue[/bold yellow]",
        border_style="green",
        width=_GAME_PANEL_W,
        height=_GAME_PANEL_H,
    )

    buf.seek(0)
    buf.truncate()
    console.print(game_panel, end="")
    text = buf.getvalue()
    text = text.replace("\n", "\r\n")
    return _HIDE_CURSOR + _HOME + text.encode() + _CLEAR_BELOW + _SHOW_CURSOR


class HumanPlayer(Player):
    """Interactive terminal player with rich display.

    Puts the terminal in raw mode, relays keystrokes to the game,
    and renders the parsed game screen inside bordered panels using
    the ``rich`` library.
    """

    def play(self, game: RogueGame, stdin: Any = None) -> None:
        """Run an interactive loop forwarding terminal I/O.

        Press Ctrl-C to quit.
        """
        fd_in = (stdin or sys.stdin).fileno()
        old_settings = termios.tcgetattr(fd_in)
        try:
            tty.setraw(fd_in)
            self._io_loop(game, fd_in)
        finally:
            termios.tcsetattr(fd_in, termios.TCSADRAIN, old_settings)
            os.write(sys.stdout.fileno(), _SHOW_CURSOR)

    @staticmethod
    def _io_loop(game: RogueGame, fd_in: int) -> None:
        """Bidirectional relay between the human's terminal and Rogue."""
        frogue = game.output_fd
        trogue = game.input_fd
        stdout_fd = sys.stdout.fileno()

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=_CONSOLE_W)

        def redraw() -> None:
            screen = game.screen
            frame = _render_frame(console, buf, screen.characters)
            os.write(stdout_fd, frame)

        os.write(stdout_fd, _CLEAR + _HOME)
        redraw()

        try:
            while game.is_running():
                rlist, _, _ = select.select([frogue, fd_in], [], [], 0.1)
                if not rlist:
                    continue

                if frogue in rlist:
                    try:
                        data = os.read(frogue, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    game.feed(data)
                    while True:
                        r2, _, _ = select.select([frogue], [], [], 0.02)
                        if not r2:
                            break
                        try:
                            more = os.read(frogue, 4096)
                        except OSError:
                            break
                        if not more:
                            break
                        game.feed(more)
                    redraw()

                if fd_in in rlist:
                    data = os.read(fd_in, 1024)
                    if not data or b"\x03" in data:
                        break
                    os.write(trogue, _translate_keys(data))
        except KeyboardInterrupt:
            pass
        finally:
            os.write(stdout_fd, _CLEAR + _HOME + _SHOW_CURSOR)
