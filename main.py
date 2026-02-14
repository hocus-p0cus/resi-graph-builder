import argparse
import json
from dataclasses import dataclass
from typing import List

from models import PropagationEdge
from inmemory_repository import InMemoryDungeonRepository
from services import ResilienceCalculator, PropagationGraphBuilder

@dataclass(frozen=True)
class Config:
    region: str = "eu"
    season: str = "tww-season3"
    resi_key_level: int = 20
    max_level: int = 25

    @property
    def db_path(self) -> str:
        return f"{self.season}-{self.region}.db"

    @property
    def output_prefix(self) -> str:
        return f"{self.season}-{self.region}-resi{self.resi_key_level}"

class ConfigLoader:
    
    @staticmethod
    def from_json(path: str = "resi_relations_config.json") -> Config:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return Config(
            region=data.get("region", "eu"),
            season=data.get("season", "tww-season3"),
            resi_key_level=data.get("resi_key_level", 20),
            max_level=data.get("max_level", 25),
        )

class DungeonConfigLoader:
    
    @staticmethod
    def load(path: str = "dungeons.json") -> tuple[List[str], dict[str, str]]:
        with open(path, "r", encoding="utf-8") as f:
            short_map = json.load(f)
        all_dungeons = list(short_map.keys())
        return all_dungeons, short_map

class EdgeSerializer:
    """Utility class for serializing edges to JSON."""
    
    @staticmethod
    def serialize(edges: List, dungeon_short: dict[str, str]) -> List[dict]:
        """Group edges by (source, target) and collect labels."""
        from collections import defaultdict
        
        edge_groups = defaultdict(list)
        for edge in edges:
            key = (edge.source, edge.target)
            edge_groups[key].append(edge.to_label(dungeon_short))
        
        return [
            {"source": src, "target": tgt, "labels": labels}
            for (src, tgt), labels in edge_groups.items()
        ]

class ResultWriter:
    
    def __init__(self, output_prefix: str):
        self.output_prefix = output_prefix
    
    def write_timestamps(self, timestamps: dict[str, str]):
        filepath = f"{self.output_prefix}_timestamps.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(timestamps, f, ensure_ascii=False, indent=2, sort_keys=True)
        return filepath
    
    def write_edges(self, edges: List[dict], edge_type: str):
        filepath = f"{self.output_prefix}_{edge_type}_edges.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(edges, f, ensure_ascii=False, indent=2)
        return filepath

class AnalysisOrchestrator:
    """
    Facade pattern - Provides simplified interface to complex subsystems.
    Coordinates the entire analysis workflow.
    """
    
    def __init__(self, config: Config, dungeons: List[str], dungeon_short: dict[str, str]):
        self.config = config
        self.dungeons = dungeons
        self.dungeon_short = dungeon_short
        
        # Dependency Injection - components can be swapped for testing
        self.repository = InMemoryDungeonRepository(config.db_path)
        self.resilience_calculator = ResilienceCalculator(self.repository)
        self.graph_builder = PropagationGraphBuilder(self.repository, self.resilience_calculator)
        self.result_writer = ResultWriter(config.output_prefix)
    
    def run_analysis(self) -> dict:
        """Execute the complete analysis pipeline."""
        
        # Step 1: Load characters
        characters = self.repository.get_all_characters()
        print(f"Found {len(characters)} characters.")
        
        # Step 2: Find resilient timestamps
        timestamps = self._find_resilient_timestamps(characters)
        print(f"✅ {len(timestamps)} characters reached resilience ≥ +{self.config.resi_key_level}")

        if len(timestamps) == 0:
            return None
        
        # Step 3: Build propagation graph
        resilient_edges, non_resilient_edges = self._build_propagation_graph(characters, timestamps)
        print(f"Built {len(resilient_edges)} resilient edges and {len(non_resilient_edges)} non-resilient edges")
        
        # Step 4: Serialize and write results
        results = self._write_results(timestamps, resilient_edges, non_resilient_edges)
        
        return results
    
    def _find_resilient_timestamps(self, characters: List[str]) -> dict[str, str]:
        """Find when each character achieved resilience."""
        timestamps = {}
        
        for character_id in characters:
            date = self.resilience_calculator.find_resilience_achievement_date(
                character_id, self.config.resi_key_level, self.dungeons
            )
            if date:
                timestamps[character_id] = date
        
        return timestamps
    
    def _build_propagation_graph(self, characters: List[str],
                                timestamps: dict[str, str]) -> tuple:
        """Build the propagation graph edges."""
        resilient_edges, non_resilient_edges = self.graph_builder.build_edges(
            characters=characters,
            resilient_timestamps=timestamps,
            dungeons=self.dungeons,
            target_level=self.config.resi_key_level,
            max_level=self.config.max_level
        )
        
        return resilient_edges, non_resilient_edges
    
    def _write_results(self, timestamps: dict, resilient_edges: List, 
                      non_resilient_edges: List) -> dict:
        """Serialize and write all results to disk."""
        # Write timestamps
        ts_file = self.result_writer.write_timestamps(timestamps)
        
        # Serialize and write edges
        serialized_resilient = EdgeSerializer.serialize(resilient_edges, self.dungeon_short)
        serialized_non_resilient = EdgeSerializer.serialize(non_resilient_edges, self.dungeon_short)
        
        down_file = self.result_writer.write_edges(serialized_resilient, "down")
        non_resil_file = self.result_writer.write_edges(serialized_non_resilient, "non_resil")
        
        print(f"\n📁 Saved files:")
        print(f" - {ts_file}")
        print(f" - {down_file}")
        print(f" - {non_resil_file}")
        
        return {
            "timestamps_file": ts_file,
            "down_edges_file": down_file,
            "non_resil_edges_file": non_resil_file,
            "character_count": len(timestamps),
            "resilient_edge_count": len(resilient_edges),
            "non_resilient_edge_count": len(non_resilient_edges)
        }
    
    def cleanup(self):
        self.repository.close()

def parse_args():
    parser = argparse.ArgumentParser(description="Run WoW resilience relation analysis.")
    parser.add_argument("--region", help="Region code, e.g. eu or us")
    parser.add_argument("--season", help="Season identifier, e.g. tww-season3")
    parser.add_argument("--resi-key-level", type=int, help="Resilience key level threshold")
    return parser.parse_args()

def load_config(args) -> Config:
    # If all three args are provided, construct config from CLI
    if args.region and args.season and args.resi_key_level:
        return Config(
            region=args.region,
            season=args.season,
            resi_key_level=args.resi_key_level
        )

    # Otherwise, fallback to JSON
    with open("resi_relations_config.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(
        region=data.get("region", "eu"),
        season=data.get("season", "tww-season3"),
        resi_key_level=data.get("resi_key_level", 20),
        max_level=data.get("max_level", 25),
    )

def main():

    args = parse_args()
    orchestrator = None

    try:
        base_config = config = load_config(args)
        dungeons, dungeon_short = DungeonConfigLoader.load()
        
        for key_level in range(base_config.resi_key_level, base_config.max_level + 1):

            config = Config(
                region=base_config.region,
                season=base_config.season,
                resi_key_level=key_level,
                max_level=base_config.max_level
            )

            print(f"\n🎯 Running analysis for resilience key level {key_level} ...")

            orchestrator = AnalysisOrchestrator(config, dungeons, dungeon_short)
            results = orchestrator.run_analysis()

            orchestrator.cleanup()
            orchestrator = None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        if orchestrator:
            orchestrator.cleanup()

if __name__ == "__main__":
    main()