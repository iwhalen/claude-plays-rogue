"""Tests for rogomatic_llm.external.game (RogueGame) with mocked subprocess/pipes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rogomatic_llm.external.game import RogueGame
from rogomatic_llm.external.screen import ScreenState

TROGUE_R, TROGUE_W = 10, 11
FROGUE_R, FROGUE_W = 12, 13


@pytest.fixture()
def game() -> RogueGame:
    return RogueGame("/usr/bin/fake-rogue", args=["--no-color"])


def _patch_pipes():
    """Patch os.pipe to return predictable FD pairs for trogue and frogue."""
    return patch(
        "rogomatic_llm.external.game.os.pipe",
        side_effect=[(TROGUE_R, TROGUE_W), (FROGUE_R, FROGUE_W)],
    )


class TestStart:
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_creates_pipes_and_spawns_process(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "/usr/bin/fake-rogue"
        assert "--no-color" in cmd
        assert "--pipe-io" in cmd
        assert "--trogue-fd" in cmd
        assert "--frogue-fd" in cmd

        trogue_idx = cmd.index("--trogue-fd")
        frogue_idx = cmd.index("--frogue-fd")
        assert cmd[trogue_idx + 1] == str(TROGUE_R)
        assert cmd[frogue_idx + 1] == str(FROGUE_W)

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_passes_game_side_fds_to_child(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        kwargs = mock_popen.call_args[1]
        assert set(kwargs["pass_fds"]) == {TROGUE_R, FROGUE_W}
        assert kwargs["close_fds"] is True

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_closes_game_side_fds_in_parent(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        mock_close.assert_any_call(TROGUE_R)
        mock_close.assert_any_call(FROGUE_W)

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_stores_player_side_fds(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        assert game._frogue_fd == FROGUE_R
        assert game._trogue_fd == TROGUE_W

    @patch("rogomatic_llm.external.game.subprocess.Popen", side_effect=OSError("spawn failed"))
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_closes_all_fds_on_popen_failure(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes(), pytest.raises(OSError, match="spawn failed"):
            game.start()

        closed_fds = {c.args[0] for c in mock_close.call_args_list}
        assert {TROGUE_R, TROGUE_W, FROGUE_R, FROGUE_W} <= closed_fds

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_start_sets_game_side_fds_inheritable(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        mock_set_inheritable.assert_any_call(TROGUE_R, True)
        mock_set_inheritable.assert_any_call(FROGUE_W, True)


class TestStop:
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_stop_terminates_process(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()
        proc = mock_popen.return_value

        game.stop()

        proc.terminate.assert_called_once()
        proc.wait.assert_called()

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_stop_closes_player_side_fds(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()
        mock_close.reset_mock()

        game.stop()

        mock_close.assert_any_call(FROGUE_R)
        mock_close.assert_any_call(TROGUE_W)

    def test_stop_on_unstarted_is_safe(self, game: RogueGame) -> None:
        game.stop()


class TestSendKeypress:
    @patch("rogomatic_llm.external.game.os.write")
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_writes_to_trogue_fd(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        mock_write: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        game.send_keypress("h")

        mock_write.assert_called_with(TROGUE_W, b"h")

    def test_raises_when_not_started(self, game: RogueGame) -> None:
        with pytest.raises(RuntimeError, match="not running"):
            game.send_keypress("j")


class TestSendCommand:
    @patch("rogomatic_llm.external.game.os.write")
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_sends_each_character(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        mock_write: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()

        game.send_command("hjk")

        assert mock_write.call_count == 3
        mock_write.assert_any_call(TROGUE_W, b"h")
        mock_write.assert_any_call(TROGUE_W, b"j")
        mock_write.assert_any_call(TROGUE_W, b"k")


class TestReadScreen:
    @patch("rogomatic_llm.external.game.select.select")
    @patch("rogomatic_llm.external.game.os.read")
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_returns_screen_state(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        mock_read: MagicMock,
        mock_select: MagicMock,
        game: RogueGame,
    ) -> None:
        mock_select.side_effect = [
            ([FROGUE_R], [], []),
            ([], [], []),
        ]
        mock_read.return_value = b"\x1b[11;41H@"

        with _patch_pipes():
            game.start()
        screen = game.read_screen()

        assert isinstance(screen, ScreenState)
        assert screen.find_player() == (10, 40)

    def test_raises_when_not_started(self, game: RogueGame) -> None:
        with pytest.raises(RuntimeError, match="not running"):
            game.read_screen()


class TestIsRunning:
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_true_when_process_alive(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        mock_popen.return_value.poll.return_value = None
        with _patch_pipes():
            game.start()
        assert game.is_running() is True

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_false_when_process_exited(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        mock_popen.return_value.poll.return_value = 0
        with _patch_pipes():
            game.start()
        assert game.is_running() is False

    def test_false_when_not_started(self, game: RogueGame) -> None:
        assert game.is_running() is False


class TestContextManager:
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_enter_starts_exit_stops(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        g = RogueGame("/usr/bin/fake-rogue")
        with _patch_pipes(), g:
            mock_popen.assert_called_once()
        mock_popen.return_value.terminate.assert_called_once()

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_stop_called_on_exception(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        g = RogueGame("/usr/bin/fake-rogue")
        with pytest.raises(ValueError, match="boom"), _patch_pipes(), g:
            raise ValueError("boom")
        mock_popen.return_value.terminate.assert_called_once()


class TestFdProperties:
    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_output_fd_returns_frogue_read_end(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()
        assert game.output_fd == FROGUE_R

    @patch("rogomatic_llm.external.game.subprocess.Popen")
    @patch("rogomatic_llm.external.game.os.set_inheritable")
    @patch("rogomatic_llm.external.game.os.close")
    def test_input_fd_returns_trogue_write_end(
        self,
        mock_close: MagicMock,
        mock_set_inheritable: MagicMock,
        mock_popen: MagicMock,
        game: RogueGame,
    ) -> None:
        with _patch_pipes():
            game.start()
        assert game.input_fd == TROGUE_W

    def test_output_fd_raises_when_not_started(self, game: RogueGame) -> None:
        with pytest.raises(RuntimeError, match="not running"):
            _ = game.output_fd

    def test_input_fd_raises_when_not_started(self, game: RogueGame) -> None:
        with pytest.raises(RuntimeError, match="not running"):
            _ = game.input_fd


class TestFeed:
    def test_feed_updates_screen_state(self, game: RogueGame) -> None:
        game.feed(b"\x1b[11;41H@")
        screen = game._parser.screen
        assert screen.find_player() == (10, 40)
