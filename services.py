from typing import List, Optional, Dict, Tuple
from tqdm import tqdm

from repository import DungeonRepository
from models import PropagationEdge

class ResilienceCalculator:
    """Service for calculating resilience levels."""
    
    def __init__(self, repository: DungeonRepository):
        self.repository = repository
    
    def calculate_resilience_level(self, character_id: str, timestamp: str,
                                   dungeons: List[str], max_level: int, min_level: int = 18) -> int:
        """
        Calculate resilient key level for a character at a given timestamp.
        Resilience = minimum of highest completed levels across all dungeons.
        MIN LEVEL IS 18 BY DEFAULT
        
        Args:
            timestamp: ISO 8601 string (e.g., "2025-09-24T20:38:11.000Z")
        """
        max_levels = self.repository.get_max_level_by_dungeon(
            character_id, dungeons, max_level, min_level, timestamp
        )
        
        # If not all dungeons completed, resilience is 0
        if len(max_levels) < len(dungeons):
            return 0
        
        return min(max_levels.values())
    
    def find_resilience_achievement_date(self, character_id: str, min_level: int,
                                        dungeons: List[str]) -> Optional[str]:
        """
        Find the date when character first achieved resilience at min_level.
        This is the latest date among all dungeon first completions.
        
        Returns: YYYY-MM-DD format string
        """
        completion_dates = []
        
        for dungeon in dungeons:
            iso_timestamp = self.repository.get_min_completion_date(character_id, dungeon, min_level)
            if not iso_timestamp:
                return None  # Didn't complete all dungeons at required level
            completion_dates.append(iso_timestamp)
        
        # Latest completion determines when resilience was achieved
        latest_timestamp = max(completion_dates)
        return latest_timestamp.split("T")[0]

class PropagationGraphBuilder:
    """Service for building propagation graphs."""
    
    def __init__(self, repository: DungeonRepository, resilience_calculator: ResilienceCalculator):
        self.repository = repository
        self.resilience_calculator = resilience_calculator
    
    def build_edges(self, characters: List[str], resilient_timestamps: Dict[str, str],
                   dungeons: List[str], target_level: int, max_level: int) -> Tuple[List[PropagationEdge], List[PropagationEdge]]:
        """
        Build propagation edges showing who influenced whom.
        Returns (resilient_edges, non_resilient_edges).
        """
        resilient_edges = []
        non_resilient_edges = []
        
        for character_id in tqdm(characters, desc="Building edges"):
            is_resilient = character_id in resilient_timestamps
            
            for dungeon in dungeons:
                completion = self.repository.get_completion(character_id, dungeon, target_level)
                if not completion:
                    continue
                
                # Skip if completed higher level earlier
                if self.repository.has_higher_completion(
                    character_id, dungeon, target_level, completion.first_completed
                ):
                    continue
                
                # Check group members
                roster = self.repository.get_roster(completion.run_id)
                
                for other_id in roster:
                    if other_id == character_id:
                        continue
                    
                    other_resilience = self.resilience_calculator.calculate_resilience_level(
                        other_id, completion.first_completed, dungeons, max_level
                    )
                    
                    if other_resilience >= target_level:
                        edge = PropagationEdge(
                            source=other_id,
                            target=character_id,
                            dungeon=dungeon,
                            run_id=completion.run_id
                        )
                        
                        if is_resilient:
                            resilient_edges.append(edge)
                        else:
                            non_resilient_edges.append(edge)
        
        return resilient_edges, non_resilient_edges