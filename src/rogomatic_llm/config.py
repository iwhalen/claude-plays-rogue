"""Global configuration for the Rogomatic for LLMs package."""

from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings

DEFAULT_ROGUE_PATH = Path("rogue-collection/build/release/rogue-collection")


class PlayerType(StrEnum):
    HUMAN = "human"
    LLM = "llm"


class RogueVersion(StrEnum):
    V3_6_3 = "Unix Rogue 3.6.3"
    V5_2_1 = "Unix Rogue 5.2.1"
    V5_3 = "Unix Rogue 5.3"
    V5_4_2 = "Unix Rogue 5.4.2"


DEFAULT_ROGUE_VERSION = RogueVersion.V5_4_2

# Must be a valid PydanticAI model that support structured output.
DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"

DEFAULT_MAX_HISTORY = 25


class CPRSettings(BaseSettings):
    """Global config for Rogomatic for LLMs."""

    player: PlayerType
    rogue_path: Path = DEFAULT_ROGUE_PATH
    rogue_version: RogueVersion = DEFAULT_ROGUE_VERSION
    model: str = DEFAULT_MODEL
    max_history: int = DEFAULT_MAX_HISTORY
