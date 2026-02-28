"""Global configuration for the Claude plays Rogue package."""

from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings

DEFAULT_ROGUE_PATH = Path("rogue-collection/build/release/rogue-collection")


class PlayerType(StrEnum):
    HUMAN = "human"
    AI = "ai"


class RogueVersion(StrEnum):
    V3_6_3 = "Unix Rogue 3.6.3"
    V5_2_1 = "Unix Rogue 5.2.1"
    V5_3 = "Unix Rogue 5.3"
    V5_4_2 = "Unix Rogue 5.4.2"


DEFAULT_ROGUE_VERSION = RogueVersion.V5_4_2


class CPRSettings(BaseSettings):
    """Global config for Claude plays Rogue."""

    player: PlayerType
    rogue_path: Path = DEFAULT_ROGUE_PATH
    rogue_version: RogueVersion = DEFAULT_ROGUE_VERSION
