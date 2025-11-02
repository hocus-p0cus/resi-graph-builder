import unittest

from main import AnalysisOrchestrator, Config

class TestEdgeSerializer(unittest.TestCase):
    """Unit tests for edge serialization."""
    
    def test_edge_grouping(self):
        """Test that edges are grouped by (source, target)."""
        from main import EdgeSerializer
        from models import PropagationEdge
        
        edges = [
            PropagationEdge("A", "B", "Dungeon1", "run1"),
            PropagationEdge("A", "B", "Dungeon2", "run2"),
            PropagationEdge("C", "D", "Dungeon1", "run3"),
        ]
        
        dungeon_short = {"Dungeon1": "D1", "Dungeon2": "D2"}
        
        result = EdgeSerializer.serialize(edges, dungeon_short)
        
        # Should have 2 groups: (A,B) and (C,D)
        self.assertEqual(len(result), 2)
        
        # Find A->B group
        ab_group = next(g for g in result if g["source"] == "A")
        self.assertEqual(len(ab_group["labels"]), 2)
        self.assertIn("D1#run1", ab_group["labels"])
        self.assertIn("D2#run2", ab_group["labels"])

class TestConfigLoader(unittest.TestCase):
    """Unit tests for configuration loading."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        self.assertEqual(config.region, "eu")
        self.assertEqual(config.season, "tww-season3")
        self.assertEqual(config.resi_key_level, 20)
        self.assertEqual(config.max_level, 25)
    
    def test_config_paths(self):
        """Test that config generates correct paths."""
        config = Config(region="us", season="test-s1", resi_key_level=18)
        
        self.assertEqual(config.db_path, "test-s1-us.db")
        self.assertEqual(config.output_prefix, "test-s1-us-resi18")