import unittest

from services import ResilienceCalculator
from tests.test_services import MockDungeonRepository

class TestMockRepository(unittest.TestCase):
    """Tests using mock repository."""
    
    def test_resilience_with_mock(self):
        """Test resilience calculation with mocked data."""
        #from tests.mocks import MockDungeonRepository
        
        mock_repo = MockDungeonRepository()
        mock_repo.max_levels = {
            "test_char": {
                "Dungeon A": 20,
                "Dungeon B": 22,
                "Dungeon C": 21
            }
        }
        
        calculator = ResilienceCalculator(mock_repo)
        
        result = calculator.calculate_resilience_level(
            "test_char",
            "2025-09-24T20:38:11.000Z",
            ["Dungeon A", "Dungeon B", "Dungeon C"],
            25
        )
        
        self.assertEqual(result, 20)  # Minimum of [20, 22, 21]