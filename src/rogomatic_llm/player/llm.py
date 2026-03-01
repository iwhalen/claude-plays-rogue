"""AI player powered by an LLM via PydanticAI."""

from __future__ import annotations

import os
import select
import time
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from rogomatic_llm.player.base import PipeBasedPlayer

if TYPE_CHECKING:
    from io import StringIO

    from pydantic_ai.messages import ModelMessage
    from rich.console import Console

    from rogomatic_llm.external.game import RogueGame

SYSTEM_PROMPT = """You are an expert player of the classic dungeon crawler Rogue.
You are controlling the game by issuing keystrokes. Your goal is to descend through the
Dungeons of Doom, find the Amulet of Yendor on the deepest level, and return
to the surface alive.

## Screen Layout

You receive a 24x80 character grid each turn:
- Row 0: message line (game prompts, combat results, item descriptions)
- Rows 1-22: dungeon map
- Row 23: status bar

## Status Bar Format

  Level: <dungeon_level>  Gold: <gold>  Hp: <cur>(<max>)
  Str: <cur>(<max>)  Arm: <class>  Exp: <level>/<points>

Higher armor class = better protection. Keep Hp above 50% when possible.

## Map Symbols

  @  you (the rogue)
  .  floor
  #  passage/corridor
  +  door
  -  horizontal wall
  |  vertical wall
  %  staircase (use > to descend, < to ascend)
  *  gold
  !  potion
  ?  scroll
  :  food
  )  weapon
  ]  armor
  /  wand or staff
  =  ring
  ^  trap (avoid stepping on these)
  ,  the Amulet of Yendor
  A-Z  monsters (later letters = stronger creatures)

## Movement Commands

  h  left
  l  right
  k  up
  j  down
  y  up-left
  u  up-right
  b  down-left
  n  down-right

Prefix with f to run until hitting something (e.g. fj = run down).
Uppercase runs until wall/door (e.g. H = run left to wall).

Move directly into a monster to attack it in melee.

## Action Commands

  s      search adjacent squares for hidden doors/traps
  .      rest one turn (regain some HP)
  >      descend stairs (must be standing on %)
  <      ascend stairs (must be standing on %)
  i      show inventory
  e      eat food from pack
  q      quaff (drink) a potion — followed by item letter
  r      read a scroll — followed by item letter
  w      wield a weapon — followed by item letter
  W      wear armor — followed by item letter
  T      take off current armor
  P      put on a ring — followed by item letter
  R      remove a ring
  d      drop an item — followed by item letter
  t      throw an item — followed by direction key, then item letter
  z      zap a wand/staff — followed by direction key
  ,      pick up item on floor (if auto-pickup is off)

## Message Handling

When "--More--" appears on the message line, you MUST respond with a single
space " " to continue. When you see "[press return to continue]", respond
with a newline (Enter key = "\\r").

When the game asks a yes/no question (e.g. "Do you wish to see the inventory?"),
respond with "n" unless you need the information.

When the game presents a menu or inventory screen and is waiting for input,
respond with the appropriate item letter or " " / Escape to dismiss.

## Strategy

1. EXPLORE: Move through rooms and corridors systematically. Search walls
(press s multiple times) near dead ends to find hidden doors.
2. COLLECT: Pick up gold, food, weapons, armor, potions, scrolls, and rings.
Wield better weapons (w) and wear better armor (W) when found.
3. SURVIVE: Eat food when you see "hungry" or "weak" on the message line —
starvation kills. Rest with . when HP is low and no enemies are near.
4. FIGHT SMART: Engage weak monsters (early alphabet) in melee. For dangerous
monsters (late alphabet), use ranged attacks (throw items with t, zap wands
with z) or retreat through corridors where they can only approach one at a time.
5. DESCEND: Once a level is explored and cleared, find stairs (%) and descend
with >. Your goal is to reach the bottom.
6. IDENTIFY: Use scrolls and potions to discover their effects. Remember what
each color/label does across the session.

## Response Format

Respond with the keystrokes for ONE logical action at a time.

Examples of single actions:
- Move one step: "h" or "j" or "k" or "l" (or diagonal: "y" "u" "b" "n")
- Run in a direction: "fj" or "fl"
- Go downstairs: ">"
- Eat food: "ea" (eat, then select item 'a')
- Quaff potion: "qb" (quaff item 'b')
- Wield weapon: "wc" (wield item 'c')
- Search for doors: "s"
- Rest: "."
- Dismiss --More--: " "

Keep your reasoning brief. Focus on what you see and what to do next.
"""


class RogueAction(BaseModel):
    """Structured output from the LLM."""

    reasoning: str = Field(
        description="Brief analysis of the current situation and chosen action"
    )
    keys: list[str] = Field(
        description="Keystrokes to send to Rogue, one action list per element.",
    )


class LLMPlayer(PipeBasedPlayer):
    """LLM-powered Rogue player using PydanticAI."""

    def __init__(self, model: str, max_history: int = 25) -> None:
        self._agent = Agent(
            model,
            system_prompt=SYSTEM_PROMPT,
            output_type=RogueAction,
        )
        self._max_history = max_history

    def _io_loop(
        self,
        game: RogueGame,
        fd_in: int,
        stdout_fd: int,
        console: Console,
        buf: StringIO,
    ) -> None:
        """AI-driven game loop: observe screen, ask LLM, send keystrokes."""
        self._drain_initial(game)
        self._redraw(game, stdout_fd, console, buf)

        history: list[ModelMessage] = []
        turn = 0

        try:
            while game.is_running():
                if self._check_ctrl_c(fd_in):
                    break

                prompt = self._build_prompt(game, turn=turn)
                result = self._agent.run_sync(
                    prompt,
                    message_history=history or None,
                )
                history = self._trim_history(result.all_messages())

                keys = result.output.keys
                os.write(game.input_fd, "".join(keys).encode("latin-1"))

                time.sleep(0.05)

                self._drain_and_redraw(game, stdout_fd, console, buf)
                turn += 1
        except KeyboardInterrupt:
            pass
        finally:
            os.write(stdout_fd, b"\x1b[2J\x1b[H\x1b[?25h")

    def _trim_history(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """Keep only the last max_history request/response pairs.

        PydanticAI messages alternate: system parts are re-injected
        automatically, so we skip any leading system/setup messages and
        keep the trailing user+assistant pairs.
        """
        pair_count = self._max_history * 2
        if len(messages) <= pair_count:
            return list(messages)
        return list(messages[-pair_count:])

    @staticmethod
    def _build_prompt(game: RogueGame, turn: int = 0) -> str:
        """Build the user prompt from the current game screen."""
        screen = game.screen
        heading = f"=== State from turn {turn} ==="
        return f"{heading}\n\n{screen.dump()}"

    @staticmethod
    def _drain_initial(game: RogueGame) -> None:
        """Wait for the game to produce its first screen output."""
        frogue = game.output_fd
        r, _, _ = select.select([frogue], [], [], 2.0)
        if r:
            PipeBasedPlayer._drain_game_output(game)

    @staticmethod
    def _drain_and_redraw(
        game: RogueGame,
        stdout_fd: int,
        console: Console,
        buf: StringIO,
    ) -> None:
        """Drain any pending game output, then redraw."""
        frogue = game.output_fd
        r, _, _ = select.select([frogue], [], [], 0.3)
        if r:
            PipeBasedPlayer._drain_game_output(game)
        PipeBasedPlayer._redraw(game, stdout_fd, console, buf)
