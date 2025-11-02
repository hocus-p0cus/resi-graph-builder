import unittest
from unittest.mock import Mock
from datetime import datetime
from typing import List, Optional, Dict

from repository import DungeonRepository
from models import DungeonCompletion
from services import ResilienceCalculator

class MockDungeonRepository(DungeonRepository):
    """Mock repository for testing."""
    
    def __init__(self):
        self.characters = []
        self.completions = {}
        self.rosters = {}
        self.max_levels = {}
    
    def get_all_characters(self) -> List[str]:
        return self.characters
    
    def get_completion(self, character_id: str, dungeon: str, level: int) -> Optional[DungeonCompletion]:
        key = (character_id, dungeon, level)
        return self.completions.get(key)
    
    def has_higher_completion(self, character_id: str, dungeon: str, level: int, before: str) -> bool:
        return False  # Simplified for testing
    
    def get_max_level_by_dungeon(self, character_id: str, dungeons: List[str],
                                max_level: int, min_level: int, before: str) -> dict[str, int]:
        return self.max_levels.get(character_id, {})
    
    def get_min_completion_date(self, character_id: str, dungeon: str, min_level: int) -> Optional[str]:
        return None
    
    def get_roster(self, run_id: str) -> List[str]:
        return self.rosters.get(run_id, [])

class TestResilienceCalculator(unittest.TestCase):
    
    def setUp(self):
        self.repo = MockDungeonRepository()
        self.calculator = ResilienceCalculator(self.repo)
    
    def test_full_resilience(self):
        """Test character with all dungeons completed."""
        self.repo.max_levels = {
            "char1": {"dng1": 20, "dng2": 21, "dng3": 20}
        }
        
        result = self.calculator.calculate_resilience_level(
            "char1", "2025-09-24T20:38:11.000Z", ["dng1", "dng2", "dng3"], 25
        )
        
        self.assertEqual(result, 20)  # Minimum of [20, 21, 20]
    
    def test_incomplete_dungeons(self):
        """Test character missing dungeon completions."""
        self.repo.max_levels = {
            "char1": {"dng1": 20, "dng2": 21}  # Missing dng3
        }
        
        result = self.calculator.calculate_resilience_level(
            "char1", "2025-09-24T20:38:11.000Z", ["dng1", "dng2", "dng3"], 25
        )
        
        self.assertEqual(result, 0)  # Not resilient

if __name__ == '__main__':
    unittest.main()