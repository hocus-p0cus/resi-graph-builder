from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Character:
    """Represents a WoW character."""
    character_id: str

@dataclass(frozen=True)
class DungeonCompletion:
    """Represents a completed dungeon run."""
    character_id: str
    dungeon_name: str
    difficulty_level: int
    first_completed: str  # ISO 8601 format: 2025-09-24T20:38:11.000Z
    run_id: str

@dataclass(frozen=True)
class ResilienceAchievement:
    """Represents when a character achieved resilience."""
    character_id: str
    date_achieved: str  # YYYY-MM-DD format
    level: int

@dataclass(frozen=True)
class PropagationEdge:
    """Represents an influence edge between two characters."""
    source: str
    target: str
    dungeon: str
    run_id: str
    
    def to_label(self, dungeon_short: dict[str, str]) -> str:
        return f"{dungeon_short[self.dungeon]}#{self.run_id}"