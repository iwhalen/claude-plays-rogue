"""Tests for cpr.player.human (HumanPlayer)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cpr.external.screen import ScreenState
from cpr.player.human import HumanPlayer, _translate_keys


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


class TestPlay:
    @patch.object(HumanPlayer, "_io_loop")
    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.termios.tcsetattr")
    @patch("cpr.player.human.tty.setraw")
    @patch("cpr.player.human.termios.tcgetattr", return_value=[1, 2, 3])
    def test_puts_terminal_in_raw_mode_and_restores(
        self,
        mock_tcgetattr: MagicMock,
        mock_setraw: MagicMock,
        mock_tcsetattr: MagicMock,
        mock_write: MagicMock,
        mock_io_loop: MagicMock,
        player: HumanPlayer,
        mock_game: MagicMock,
    ) -> None:
        stdin = MagicMock()
        stdin.fileno.return_value = 0

        player.play(mock_game, stdin=stdin)

        mock_tcgetattr.assert_called_once_with(0)
        mock_setraw.assert_called_once_with(0)
        mock_tcsetattr.assert_called_once()

    @patch.object(HumanPlayer, "_io_loop", side_effect=RuntimeError("boom"))
    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.termios.tcsetattr")
    @patch("cpr.player.human.tty.setraw")
    @patch("cpr.player.human.termios.tcgetattr", return_value=[1, 2, 3])
    def test_restores_terminal_on_exception(
        self,
        mock_tcgetattr: MagicMock,
        mock_setraw: MagicMock,
        mock_tcsetattr: MagicMock,
        mock_write: MagicMock,
        mock_io_loop: MagicMock,
        player: HumanPlayer,
        mock_game: MagicMock,
    ) -> None:
        stdin = MagicMock()
        stdin.fileno.return_value = 0

        with pytest.raises(RuntimeError, match="boom"):
            player.play(mock_game, stdin=stdin)

        mock_tcsetattr.assert_called_once()


class TestIOLoop:
    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.os.read")
    @patch("cpr.player.human.select.select")
    def test_feeds_game_output_to_parser(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.side_effect = [True, False]
        mock_select.side_effect = [
            ([mock_game.output_fd], [], []),
            ([], [], []),  # drain
        ]
        mock_read.return_value = b"\x1b[11;41H@"

        HumanPlayer._io_loop(mock_game, fd_in=0)

        mock_game.feed.assert_called_once_with(b"\x1b[11;41H@")

    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.os.read")
    @patch("cpr.player.human.select.select")
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

        HumanPlayer._io_loop(mock_game, fd_in=fd_in)

        mock_write.assert_any_call(mock_game.input_fd, b"h")

    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.os.read")
    @patch("cpr.player.human.select.select")
    def test_stops_on_eof_from_game(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.return_value = True
        mock_select.return_value = ([mock_game.output_fd], [], [])
        mock_read.return_value = b""

        HumanPlayer._io_loop(mock_game, fd_in=0)

        mock_game.feed.assert_not_called()

    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.os.read")
    @patch("cpr.player.human.select.select")
    def test_handles_keyboard_interrupt(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_game: MagicMock,
    ) -> None:
        mock_game.is_running.return_value = True
        mock_select.side_effect = KeyboardInterrupt

        HumanPlayer._io_loop(mock_game, fd_in=0)

    @patch("cpr.player.human.os.write")
    @patch("cpr.player.human.os.read")
    @patch("cpr.player.human.select.select")
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

        HumanPlayer._io_loop(mock_game, fd_in=0)

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
