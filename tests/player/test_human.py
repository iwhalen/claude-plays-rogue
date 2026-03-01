"""Tests for rogomatic_llm.player.human (HumanPlayer)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from rogomatic_llm.external.screen import ScreenState
from rogomatic_llm.player.human import HumanPlayer, _translate_keys


@pytest.fixture()
def player() -> HumanPlayer:
    return HumanPlayer()


@pytest.fixture()
def mock_game() -> MagicMock:
    game = MagicMock()
    game.output_fd = 12
    game.input_fd = 11
    game.is_running.return_value = False
    game.screen = ScreenState.empty()
    return game


@pytest.fixture()
def mock_stdin() -> MagicMock:
    stdin = MagicMock()
    stdin.fileno.return_value = 0
    return stdin


class TestPlay:
    @patch.object(HumanPlayer, "_io_loop")
    @patch("rogomatic_llm.player.base.os.write")
    @patch("rogomatic_llm.player.base.termios.tcsetattr")
    @patch("rogomatic_llm.player.base.tty.setraw")
    @patch("rogomatic_llm.player.base.termios.tcgetattr", return_value=[1, 2, 3])
    def test_puts_terminal_in_raw_mode_and_restores(
        self,
        mock_tcgetattr: MagicMock,
        mock_setraw: MagicMock,
        mock_tcsetattr: MagicMock,
        mock_write: MagicMock,
        mock_io_loop: MagicMock,
        player: HumanPlayer,
        mock_game: MagicMock,
        mock_stdin: MagicMock,
    ) -> None:
        with patch("rogomatic_llm.player.base.sys.stdin", mock_stdin):
            player.play(mock_game)

        mock_tcgetattr.assert_called_once_with(0)
        mock_setraw.assert_called_once_with(0)
        mock_tcsetattr.assert_called_once()

    @patch.object(HumanPlayer, "_io_loop", side_effect=RuntimeError("boom"))
    @patch("rogomatic_llm.player.base.os.write")
    @patch("rogomatic_llm.player.base.termios.tcsetattr")
    @patch("rogomatic_llm.player.base.tty.setraw")
    @patch("rogomatic_llm.player.base.termios.tcgetattr", return_value=[1, 2, 3])
    def test_restores_terminal_on_exception(
        self,
        mock_tcgetattr: MagicMock,
        mock_setraw: MagicMock,
        mock_tcsetattr: MagicMock,
        mock_write: MagicMock,
        mock_io_loop: MagicMock,
        player: HumanPlayer,
        mock_game: MagicMock,
        mock_stdin: MagicMock,
    ) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            with patch("rogomatic_llm.player.base.sys.stdin", mock_stdin):
                player.play(mock_game)

        mock_tcsetattr.assert_called_once()


class TestIOLoop:
    @patch("rogomatic_llm.player.human.os.write")
    @patch("rogomatic_llm.player.human.os.read")
    @patch("rogomatic_llm.player.human.select.select")
    @patch("rogomatic_llm.player.base.select.select")
    def test_feeds_game_output_to_parser(
        self,
        mock_base_select: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.side_effect = [True, False]
        mock_select.side_effect = [
            ([mock_game.output_fd], [], []),
            ([], [], []),
        ]
        mock_base_select.return_value = ([], [], [])
        mock_read.return_value = b"\x1b[11;41H@"

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=86)
        HumanPlayer()._io_loop(mock_game, fd_in=0, stdout_fd=1, console=console, buf=buf)

        mock_game.feed.assert_called_once_with(b"\x1b[11;41H@")

    @patch("rogomatic_llm.player.human.os.write")
    @patch("rogomatic_llm.player.human.os.read")
    @patch("rogomatic_llm.player.human.select.select")
    def test_forwards_stdin_to_game(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        fd_in = 0
        mock_game.is_running.side_effect = [True, False]
        mock_select.return_value = ([fd_in], [], [])
        mock_read.return_value = b"h"

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=86)
        HumanPlayer()._io_loop(mock_game, fd_in=fd_in, stdout_fd=1, console=console, buf=buf)

        mock_write.assert_any_call(mock_game.input_fd, b"h")

    @patch("rogomatic_llm.player.human.os.write")
    @patch("rogomatic_llm.player.human.os.read")
    @patch("rogomatic_llm.player.human.select.select")
    @patch("rogomatic_llm.player.base.select.select")
    def test_stops_on_eof_from_game(
        self,
        mock_base_select: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.return_value = True
        mock_select.return_value = ([mock_game.output_fd], [], [])
        mock_base_select.return_value = ([], [], [])
        mock_read.return_value = b""

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=86)
        HumanPlayer()._io_loop(mock_game, fd_in=0, stdout_fd=1, console=console, buf=buf)

        mock_game.feed.assert_not_called()

    @patch("rogomatic_llm.player.human.os.write")
    @patch("rogomatic_llm.player.human.os.read")
    @patch("rogomatic_llm.player.human.select.select")
    def test_handles_keyboard_interrupt(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.return_value = True
        mock_select.side_effect = KeyboardInterrupt

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=86)
        HumanPlayer()._io_loop(mock_game, fd_in=0, stdout_fd=1, console=console, buf=buf)

    @patch("rogomatic_llm.player.human.os.write")
    @patch("rogomatic_llm.player.human.os.read")
    @patch("rogomatic_llm.player.human.select.select")
    def test_exits_on_ctrl_c(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.return_value = True
        mock_select.return_value = ([0], [], [])
        mock_read.return_value = b"\x03"

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=86)
        HumanPlayer()._io_loop(mock_game, fd_in=0, stdout_fd=1, console=console, buf=buf)

        for c in mock_write.call_args_list:
            assert c[0][0] != mock_game.input_fd


class TestTranslateKeys:
    def test_arrow_up(self) -> None:
        assert _translate_keys(b"\x1b[A") == b"k"

    def test_arrow_down(self) -> None:
        assert _translate_keys(b"\x1b[B") == b"j"

    def test_arrow_right(self) -> None:
        assert _translate_keys(b"\x1b[C") == b"l"

    def test_arrow_left(self) -> None:
        assert _translate_keys(b"\x1b[D") == b"h"

    def test_passthrough_normal_keys(self) -> None:
        assert _translate_keys(b"hjkl") == b"hjkl"

    def test_mixed_input(self) -> None:
        assert _translate_keys(b"a\x1b[Ab") == b"akb"

    def test_application_mode_arrows(self) -> None:
        assert _translate_keys(b"\x1bOA") == b"k"
        assert _translate_keys(b"\x1bOB") == b"j"
        assert _translate_keys(b"\x1bOC") == b"l"
        assert _translate_keys(b"\x1bOD") == b"h"
