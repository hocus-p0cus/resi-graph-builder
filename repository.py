from abc import ABC, abstractmethod
from typing import List, Optional
from models import DungeonCompletion

class DungeonRepository(ABC):
    """Abstract repository for dungeon data access."""
    
    @abstractmethod
    def get_all_characters(self) -> List[str]:
        """Get all unique character IDs."""
        pass
    
    @abstractmethod
    def get_completion(self, character_id: str, dungeon: str, level: int) -> Optional[DungeonCompletion]:
        """Get first completion for a character at a specific level."""
        pass
    
    @abstractmethod
    def has_higher_completion(self, character_id: str, dungeon: str, level: int, before: str) -> bool:
        """Check if character completed higher level before given time (ISO 8601 string)."""
        pass
    
    @abstractmethod
    def get_max_level_by_dungeon(self, character_id: str, dungeons: List[str], 
                                  max_level: int, min_level: int, before: str) -> dict[str, int]:
        """Get maximum completed level for each dungeon before timestamp (ISO 8601 string)."""
        pass
    
    @abstractmethod
    def get_min_completion_date(self, character_id: str, dungeon: str, min_level: int) -> Optional[str]:
        """Get earliest date character completed dungeon at min_level or higher (ISO 8601 string)."""
        pass
    
    @abstractmethod
    def get_roster(self, run_id: str) -> List[str]:
        """Get all character IDs in a dungeon run."""
        pass