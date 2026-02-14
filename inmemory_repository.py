import sqlite3
from collections import defaultdict
from typing import List, Optional, Dict

from repository import DungeonRepository
from models import DungeonCompletion


class InMemoryDungeonRepository(DungeonRepository):
    """
    DungeonRepository backed entirely by in-memory dictionaries.
    Loads all data from a SQLite database once at construction time,
    then answers every query from memory with no further I/O.
    """

    def __init__(self, db_path: str):
        # character_id -> dungeon_name -> level -> DungeonCompletion
        self._completions: Dict[str, Dict[str, Dict[int, DungeonCompletion]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        # run_id -> list of character_ids
        self._rosters: Dict[str, List[str]] = {}

        self._load(db_path)

    # ------------------------------------------------------------------ #
    #  Data loading
    # ------------------------------------------------------------------ #

    def _load(self, db_path: str):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Load completions
        cursor.execute("""
            SELECT character_id, dungeon_name, difficulty_level,
                   first_completed, first_run_id
            FROM character_dungeon_stats
        """)
        for row in cursor.fetchall():
            comp = DungeonCompletion(
                character_id=row[0],
                dungeon_name=row[1],
                difficulty_level=row[2],
                first_completed=row[3],
                run_id=str(row[4]),
            )
            self._completions[comp.character_id][comp.dungeon_name][comp.difficulty_level] = comp

        # Load rosters
        cursor.execute("SELECT run_id, character_id FROM roster ORDER BY run_id")
        temp: Dict[str, List[str]] = defaultdict(list)
        for row in cursor.fetchall():
            temp[str(row[0])].append(row[1])
        self._rosters = dict(temp)

        conn.close()

    # ------------------------------------------------------------------ #
    #  DungeonRepository interface
    # ------------------------------------------------------------------ #

    def get_all_characters(self) -> List[str]:
        return list(self._completions.keys())

    def get_completion(self, character_id: str, dungeon: str, level: int) -> Optional[DungeonCompletion]:
        return self._completions.get(character_id, {}).get(dungeon, {}).get(level)

    def has_higher_completion(self, character_id: str, dungeon: str, level: int, before: str) -> bool:
        dungeon_levels = self._completions.get(character_id, {}).get(dungeon, {})
        for comp_level, comp in dungeon_levels.items():
            if comp_level > level and comp.first_completed < before:
                return True
        return False

    def get_max_level_by_dungeon(self, character_id: str, dungeons: List[str],
                                  max_level: int, min_level: int, before: str) -> Dict[str, int]:
        result = {}
        char_completions = self._completions.get(character_id, {})

        for dungeon in dungeons:
            dungeon_levels = char_completions.get(dungeon, {})
            best = 0
            for level, comp in dungeon_levels.items():
                if min_level <= level <= max_level and comp.first_completed < before:
                    best = max(best, level)
            if best > 0:
                result[dungeon] = best

        return result

    def get_min_completion_date(self, character_id: str, dungeon: str, min_level: int) -> Optional[str]:
        dungeon_levels = self._completions.get(character_id, {}).get(dungeon, {})
        earliest = None
        for level, comp in dungeon_levels.items():
            if level >= min_level:
                if earliest is None or comp.first_completed < earliest:
                    earliest = comp.first_completed
        return earliest

    def get_roster(self, run_id: str) -> List[str]:
        return self._rosters.get(run_id, [])

    def close(self):
        pass  # Nothing to close — all in memory