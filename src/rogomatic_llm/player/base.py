"""Abstract base classes for Rogue players."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from abc import ABC, abstractmethod
from io import StringIO
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from rogomatic_llm.external.game import RogueGame

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


def render_frame(
    console: Console,
    buf: StringIO,
    screen_chars: list[list[str]],
) -> bytes:
    """Render the game screen as a rich panel formatted for a raw-mode terminal.

    Newlines are converted to ``\\r\\n`` for raw-mode compatibility.
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


class Player(ABC):
    """Contract for a player that interacts with a running Rogue game."""

    @abstractmethod
    def play(self, game: RogueGame) -> None:
        """Take control and play the game until it ends or the player quits."""


class PipeBasedPlayer(Player):
    """Base class for players that communicate with Rogue over pipes.

    Handles terminal raw-mode setup/teardown and provides helpers for
    draining game output, feeding the VT100 parser, and rendering the
    screen via Rich panels.  Subclasses implement :meth:`_io_loop` to
    define how input is sourced (keyboard vs. LLM).
    """

    def play(self, game: RogueGame) -> None:
        fd_in = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd_in)
        try:
            tty.setraw(fd_in)
            buf = StringIO()
            console = Console(file=buf, force_terminal=True, width=_CONSOLE_W)
            stdout_fd = sys.stdout.fileno()
            os.write(stdout_fd, _CLEAR + _HOME)
            self._io_loop(game, fd_in, stdout_fd, console, buf)
        finally:
            termios.tcsetattr(fd_in, termios.TCSADRAIN, old_settings)
            os.write(sys.stdout.fileno(), _SHOW_CURSOR)

    @abstractmethod
    def _io_loop(
        self,
        game: RogueGame,
        fd_in: int,
        stdout_fd: int,
        console: Console,
        buf: StringIO,
    ) -> None:
        """Main I/O loop — subclasses define how input is produced."""

    @staticmethod
    def _redraw(
        game: RogueGame,
        stdout_fd: int,
        console: Console,
        buf: StringIO,
    ) -> None:
        """Render the current game screen to the terminal."""
        frame = render_frame(console, buf, game.screen.characters)
        os.write(stdout_fd, frame)

    @staticmethod
    def _drain_game_output(game: RogueGame) -> bool:
        """Read all available bytes from the game pipe and feed the parser.

        Returns False if the pipe is closed (game exited).
        """
        frogue = game.output_fd
        try:
            data = os.read(frogue, 4096)
        except OSError:
            return False
        if not data:
            return False
        game.feed(data)
        while True:
            r, _, _ = select.select([frogue], [], [], 0.02)
            if not r:
                break
            try:
                more = os.read(frogue, 4096)
            except OSError:
                break
            if not more:
                break
            game.feed(more)
        return True

    @staticmethod
    def _check_ctrl_c(fd_in: int) -> bool:
        """Non-blocking check for Ctrl-C on stdin. Returns True if detected."""
        r, _, _ = select.select([fd_in], [], [], 0)
        if r:
            data = os.read(fd_in, 1024)
            if not data or b"\x03" in data:
                return True
        return False
