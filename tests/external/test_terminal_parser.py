"""Tests for rogomatic_llm.external.terminal_parser."""

from __future__ import annotations

from rogomatic_llm.external.terminal_parser import TerminalParser


class TestCursorMovement:
    def test_move_to_position(self, cursor_move_bytes: bytes) -> None:
        p = TerminalParser()
        p.feed(cursor_move_bytes)  # ESC[5;20H → row 4, col 19
        s = p.screen
        assert s.cursor_row == 4
        assert s.cursor_col == 19

    def test_move_to_origin(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[10;10H")
        p.feed(b"\x1b[1;1H")  # row 0, col 0
        s = p.screen
        assert s.cursor_row == 0
        assert s.cursor_col == 0

    def test_move_with_no_params_goes_to_origin(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[5;5H")
        p.feed(b"\x1b[H")  # no params → origin
        s = p.screen
        assert s.cursor_row == 0
        assert s.cursor_col == 0

    def test_move_clamped_to_bounds(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[999;999H")
        s = p.screen
        assert s.cursor_row == 23
        assert s.cursor_col == 79


class TestPrintableCharacters:
    def test_write_at_cursor(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")  # row 0, col 0
        p.feed(b"A")
        s = p.screen
        assert s.characters[0][0] == "A"
        assert s.cursor_col == 1

    def test_write_string_advances_cursor(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")
        p.feed(b"Hello")
        s = p.screen
        assert "".join(s.characters[0][:5]) == "Hello"
        assert s.cursor_col == 5

    def test_write_at_specific_position(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[3;10H")  # row 2, col 9
        p.feed(b"X")
        s = p.screen
        assert s.characters[2][9] == "X"


class TestClearScreen:
    def test_clear_resets_all_cells(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")
        p.feed(b"ABCD")
        p.feed(b"\x0c")  # Ctrl-L
        s = p.screen
        for row in s.characters:
            assert all(ch == " " for ch in row)

    def test_clear_resets_cursor(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[10;40H")
        p.feed(b"\x0c")
        s = p.screen
        assert s.cursor_row == 0
        assert s.cursor_col == 0


class TestClearToEndOfLine:
    def test_clears_from_cursor_to_end(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")
        p.feed(b"Hello World This Is Rogue")
        p.feed(b"\x1b[1;6H")  # row 0, col 5
        p.feed(b"\x1b[K")
        s = p.screen
        assert "".join(s.characters[0][:5]) == "Hello"
        assert all(ch == " " for ch in s.characters[0][5:])

    def test_clear_eol_at_start_clears_entire_row(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")
        p.feed(b"XXXXXXXXXXXXXXXX")
        p.feed(b"\x1b[1;1H")
        p.feed(b"\x1b[K")
        s = p.screen
        assert all(ch == " " for ch in s.characters[0])


class TestLineFeed:
    def test_lf_advances_row(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")
        p.feed(b"\n")
        s = p.screen
        assert s.cursor_row == 1

    def test_lf_does_not_exceed_last_row(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[24;1H")  # row 23 (last)
        p.feed(b"\n")
        s = p.screen
        assert s.cursor_row == 23


class TestCarriageReturn:
    def test_cr_resets_column(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;40H")
        p.feed(b"\r")
        s = p.screen
        assert s.cursor_col == 0
        assert s.cursor_row == 0  # row unchanged


class TestBackspace:
    def test_backspace_moves_cursor_left(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;5H")  # col 4
        p.feed(b"\x08")
        s = p.screen
        assert s.cursor_col == 3

    def test_backspace_clamps_at_zero(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1H")  # col 0
        p.feed(b"\x08")
        s = p.screen
        assert s.cursor_col == 0


class TestClearToEndOfScreen:
    def test_clears_from_cursor_down(self) -> None:
        p = TerminalParser()
        # Fill rows 0-3 with X
        for r in range(4):
            p.feed(f"\x1b[{r + 1};1H".encode())
            p.feed(b"X" * 80)
        # Clear from row 1, col 40
        p.feed(b"\x1b[2;41H")  # row 1, col 40
        p.feed(b"\x1b[J")
        s = p.screen
        # Row 0 untouched
        assert s.characters[0][0] == "X"
        # Row 1 cols 0-39 untouched, 40-79 cleared
        assert s.characters[1][39] == "X"
        assert s.characters[1][40] == " "
        # Rows 2-3 fully cleared
        assert all(ch == " " for ch in s.characters[2])
        assert all(ch == " " for ch in s.characters[3])


class TestFullFrame:
    def test_sample_rogue_frame(self, sample_rogue_frame: bytes) -> None:
        p = TerminalParser()
        p.feed(sample_rogue_frame)
        s = p.screen

        assert s.message_line == "the hobbit hit you"
        assert "".join(s.characters[1][:5]) == "-----"
        assert s.find_player() == (10, 40)

    def test_deep_copy_independence(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[1;1HA")
        s1 = p.screen
        p.feed(b"B")
        s2 = p.screen
        assert s1.characters[0][0] == "A"
        assert s2.characters[0][1] == "B"
        assert s1.characters[0][1] == " "  # s1 unmodified


class TestStandoutIgnored:
    def test_standout_on_off_does_not_crash(self) -> None:
        p = TerminalParser()
        p.feed(b"\x1b[7m")  # standout on
        p.feed(b"M")
        p.feed(b"\x1b[m")  # standout off
        s = p.screen
        assert s.characters[0][0] == "M"
