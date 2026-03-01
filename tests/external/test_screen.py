"""Tests for rogomatic_llm.external.screen (ScreenState and StatusLine)."""

from __future__ import annotations

import pytest

from rogomatic_llm.external.screen import ScreenState, StatusLine


class TestScreenStateEmpty:
    def test_dimensions(self, empty_screen: ScreenState) -> None:
        assert len(empty_screen.characters) == 24
        assert all(len(row) == 80 for row in empty_screen.characters)

    def test_all_spaces(self, empty_screen: ScreenState) -> None:
        for row in empty_screen.characters:
            assert all(ch == " " for ch in row)

    def test_cursor_at_origin(self, empty_screen: ScreenState) -> None:
        assert empty_screen.cursor_row == 0
        assert empty_screen.cursor_col == 0


class TestStatusLineParse:
    def test_parse_v53_format(self, rogue_status_line: str) -> None:
        status = StatusLine.parse(rogue_status_line)
        assert status is not None
        assert status.dungeon_level == 3
        assert status.gold == 142
        assert status.current_hp == 10
        assert status.max_hp == 12
        assert status.current_strength == 16
        assert status.max_strength == 16
        assert status.armor_class == 4
        assert status.experience_level == 2
        assert status.experience_points == 27

    def test_parse_returns_none_for_garbage(self) -> None:
        assert StatusLine.parse("not a status line") is None

    def test_parse_returns_none_for_empty(self) -> None:
        assert StatusLine.parse("") is None

    def test_parse_with_large_values(self) -> None:
        line = (
            "Level: 26  Gold: 99999  Hp: 1(150)  Str: 31(31)  Arm: -3  Exp: 21/970000"
        )
        status = StatusLine.parse(line)
        assert status is not None
        assert status.dungeon_level == 26
        assert status.gold == 99999
        assert status.max_hp == 150

    def test_frozen(self, rogue_status_line: str) -> None:
        status = StatusLine.parse(rogue_status_line)
        assert status is not None
        with pytest.raises(AttributeError):
            status.gold = 0  # type: ignore[misc]


class TestScreenStateFindPlayer:
    def test_finds_player(self, screen_with_player: ScreenState) -> None:
        pos = screen_with_player.find_player()
        assert pos == (10, 40)

    def test_no_player(self, empty_screen: ScreenState) -> None:
        assert empty_screen.find_player() is None

    def test_ignores_at_in_status_row(self) -> None:
        s = ScreenState.empty()
        s.characters[23][5] = "@"
        assert s.find_player() is None

    def test_ignores_at_in_message_row(self) -> None:
        s = ScreenState.empty()
        s.characters[0][10] = "@"
        assert s.find_player() is None


class TestScreenStateMessageLine:
    def test_empty_message(self, empty_screen: ScreenState) -> None:
        assert empty_screen.message_line == ""

    def test_with_message(self) -> None:
        s = ScreenState.empty()
        msg = "the hobbit hit you"
        for i, ch in enumerate(msg):
            s.characters[0][i] = ch
        assert s.message_line == msg


class TestScreenStateStatus:
    def test_delegates_to_statusline_parse(
        self, screen_with_status: ScreenState
    ) -> None:
        status = screen_with_status.status
        assert status is not None
        assert status.dungeon_level == 3
        assert status.gold == 142

    def test_returns_none_on_empty(self, empty_screen: ScreenState) -> None:
        assert empty_screen.status is None


class TestScreenStateDump:
    def test_empty_dump_line_count(self, empty_screen: ScreenState) -> None:
        dumped = empty_screen.dump()
        lines = dumped.split("\n")
        assert len(lines) == 24

    def test_empty_dump_line_width(self, empty_screen: ScreenState) -> None:
        dumped = empty_screen.dump()
        for line in dumped.split("\n"):
            assert len(line) == 80

    def test_dump_contains_player(self, screen_with_player: ScreenState) -> None:
        dumped = screen_with_player.dump()
        assert "@" in dumped

    def test_dump_round_trips(self) -> None:
        s = ScreenState.empty()
        s.characters[5][10] = "X"
        dumped = s.dump()
        lines = dumped.split("\n")
        assert lines[5][10] == "X"
