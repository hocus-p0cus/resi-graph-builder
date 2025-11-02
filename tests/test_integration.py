import unittest
import tempfile
import sqlite3
from pathlib import Path

from models import *
from sqlite_repository import SQLiteDungeonRepository
from services import ResilienceCalculator, PropagationGraphBuilder
from main import AnalysisOrchestrator, Config

class TestIntegration(unittest.TestCase):
    """Integration tests with real SQLite database."""

    def setUp(self):
        """Create temporary database with test data."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = temp_db.name
        temp_db.close()

        self._setup_test_database()

        # Test config
        self.config = Config(
            region="test",
            season="test-season",
            resi_key_level=20,
            max_level=25
        )

        self.dungeons = ["Dungeon A", "Dungeon B", "Dungeon C"]
        self.dungeon_short = {
            "Dungeon A": "DA",
            "Dungeon B": "DB",
            "Dungeon C": "DC"
        }

        # Repository used across tests
        self.repo = None

    def tearDown(self):
        """Clean up: close repo and delete temp DB."""
        if self.repo:
            self.repo.close()
            self.repo = None

        try:
            Path(self.db_path).unlink()
        except PermissionError:
            # If the file is still locked, ignore for cleanup
            pass

    def _setup_test_database(self):
        """Create test database schema and data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE character_dungeon_stats (
                character_id TEXT,
                dungeon_name TEXT,
                difficulty_level INTEGER,
                first_completed TEXT,
                first_run_id TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE roster (
                run_id TEXT,
                character_id TEXT
            )
        """)

        test_data = [
            ("char1", "Dungeon A", 20, "2025-01-01T12:00:00.000Z", "run1"),
            ("char1", "Dungeon B", 21, "2025-01-02T12:00:00.000Z", "run2"),
            ("char1", "Dungeon C", 20, "2025-01-03T12:00:00.000Z", "run3"),

            ("char2", "Dungeon A", 20, "2025-01-04T12:00:00.000Z", "run4"),
            ("char2", "Dungeon B", 20, "2025-01-05T12:00:00.000Z", "run5"),
            ("char2", "Dungeon C", 22, "2025-01-06T12:00:00.000Z", "run6"),

            ("char3", "Dungeon A", 19, "2025-01-07T12:00:00.000Z", "run7"),
            ("char3", "Dungeon B", 20, "2025-01-08T12:00:00.000Z", "run8"),
            ("char3", "Dungeon C", 18, "2025-01-09T12:00:00.000Z", "run9"),
        ]

        cursor.executemany("""
            INSERT INTO character_dungeon_stats 
            VALUES (?, ?, ?, ?, ?)
        """, test_data)

        roster_data = [
            ("run4", "char1"),
            ("run4", "char2"),
        ]

        cursor.executemany("INSERT INTO roster VALUES (?, ?)", roster_data)
        conn.commit()
        conn.close()

    def _get_repo(self):
        """Lazy initialize repo per test."""
        if not self.repo:
            self.repo = SQLiteDungeonRepository(self.db_path)
        return self.repo

    def test_resilience_calculation(self):
        repo = self._get_repo()
        calculator = ResilienceCalculator(repo)

        self.assertEqual(
            calculator.calculate_resilience_level("char1", "2025-01-10T00:00:00.000Z", self.dungeons, 25),
            20
        )

        self.assertEqual(
            calculator.calculate_resilience_level("char3", "2025-01-10T00:00:00.000Z", self.dungeons, 25),
            18
        )

    def test_achievement_date_finding(self):
        repo = self._get_repo()
        calculator = ResilienceCalculator(repo)

        self.assertEqual(
            calculator.find_resilience_achievement_date("char1", 20, self.dungeons),
            "2025-01-03"
        )

        self.assertIsNone(
            calculator.find_resilience_achievement_date("char3", 20, self.dungeons)
        )

    #def test_timestamp_string_comparison(self):
    #    self.assertTrue("2025-01-01T12:00:00.000Z" < "2025-01-02T12:00:00.000Z")
    #    self.assertTrue("2025-01-01T12:00:00.000Z" < "2025-01-01T13:00:00.000Z")
    #    timestamps = ["2025-01-01T12:00:00.000Z", "2025-01-03T12:00:00.000Z", "2025-01-02T12:00:00.000Z"]
    #    self.assertEqual(max(timestamps), "2025-01-03T12:00:00.000Z")

    def test_propagation_edge_building(self):
        repo = self._get_repo()
        calculator = ResilienceCalculator(repo)
        builder = PropagationGraphBuilder(repo, calculator)

        timestamps = {"char1": "2025-01-03", "char2": "2025-01-06"}

        resilient_edges, non_resilient_edges = builder.build_edges(
            characters=["char1", "char2", "char3"],
            resilient_timestamps=timestamps,
            dungeons=self.dungeons,
            target_level=20,
            max_level=25
        )

        self.assertTrue(any(
            e.source == "char1" and e.target == "char2" for e in resilient_edges
        ))
