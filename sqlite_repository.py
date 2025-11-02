import sqlite3
from typing import List, Optional

from repository import DungeonRepository
from models import DungeonCompletion

class SQLiteDungeonRepository(DungeonRepository):
    """SQLite implementation of DungeonRepository."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def get_all_characters(self) -> List[str]:
        self.cursor.execute("SELECT DISTINCT character_id FROM character_dungeon_stats")
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_completion(self, character_id: str, dungeon: str, level: int) -> Optional[DungeonCompletion]:
        self.cursor.execute("""
            SELECT first_completed, first_run_id
            FROM character_dungeon_stats
            WHERE character_id = ? AND dungeon_name = ? AND difficulty_level = ?
            LIMIT 1
        """, (character_id, dungeon, level))
        row = self.cursor.fetchone()
        if not row:
            return None
        return DungeonCompletion(
            character_id=character_id,
            dungeon_name=dungeon,
            difficulty_level=level,
            first_completed=row[0],  # Already in ISO 8601 format
            run_id=row[1]
        )
    
    def has_higher_completion(self, character_id: str, dungeon: str, level: int, before: str) -> bool:
        self.cursor.execute("""
            SELECT 1 FROM character_dungeon_stats
            WHERE character_id = ? AND dungeon_name = ? 
              AND difficulty_level > ? AND first_completed < ?
            LIMIT 1
        """, (character_id, dungeon, level, before))
        return self.cursor.fetchone() is not None
    
    def get_max_level_by_dungeon(self, character_id: str, dungeons: List[str], 
                                  max_level: int, min_level: int, before: str) -> dict[str, int]:
        """Optimized batch query to get max levels for all dungeons."""
        placeholders = ','.join('?' * len(dungeons))
        self.cursor.execute(f"""
            SELECT dungeon_name, MAX(difficulty_level) as max_level
            FROM character_dungeon_stats
            WHERE character_id = ?
              AND dungeon_name IN ({placeholders})
              AND difficulty_level BETWEEN ? AND ?
              AND first_completed < ?
            GROUP BY dungeon_name
        """, (character_id, *dungeons, min_level, max_level, before))
        
        return {row[0]: row[1] for row in self.cursor.fetchall()}
    
    def get_min_completion_date(self, character_id: str, dungeon: str, min_level: int) -> Optional[str]:
        self.cursor.execute("""
            SELECT MIN(first_completed)
            FROM character_dungeon_stats
            WHERE character_id = ? AND dungeon_name = ? AND difficulty_level >= ?
        """, (character_id, dungeon, min_level))
        result = self.cursor.fetchone()
        if not result or not result[0]:
            return None
        return result[0]  # Already in ISO 8601 format
    
    def get_roster(self, run_id: str) -> List[str]:
        self.cursor.execute("SELECT character_id FROM roster WHERE run_id = ?", (run_id,))
        return [row[0] for row in self.cursor.fetchall()]
    
    def close(self):
        self.conn.close()