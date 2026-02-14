import unittest
import json
import os
from pathlib import Path


BASELINE_DIR = Path("tests/baselines")
DB_DIR = Path(".")  # .db files live at project root

REGIONS = ["eu", "na"]
SEASON = "tww-season3"
KEY_LEVELS = list(range(18, 25))


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_edges(edges: list[dict]) -> set[tuple]:
    """Convert edge list to a comparable set of (source, target, frozenset(labels))."""
    result = set()
    for edge in edges:
        key = (edge["source"], edge["target"], frozenset(edge["labels"]))
        result.add(key)
    return result


def run_analysis_for(region: str, season: str, key_level: int, max_level: int = 25) -> dict:
    """Run the analysis pipeline and return paths to output files."""
    from main import Config, AnalysisOrchestrator, DungeonConfigLoader

    config = Config(
        region=region,
        season=season,
        resi_key_level=key_level,
        max_level=max_level,
    )

    dungeons, dungeon_short = DungeonConfigLoader.load()
    orchestrator = AnalysisOrchestrator(config, dungeons, dungeon_short)

    try:
        results = orchestrator.run_analysis()
        return results
    finally:
        orchestrator.cleanup()


class TestRegression(unittest.TestCase):
    """
    Run the full analysis pipeline against real .db files and compare
    outputs to known-good baselines.

    Baseline folder layout:
        tests/baselines/{region}/{season}/
            {season}-{region}-resi{level}_timestamps.json
            {season}-{region}-resi{level}_down_edges.json
            {season}-{region}-resi{level}_non_resil_edges.json
    """

    def _baseline_path(self, region: str, level: int, suffix: str) -> Path:
        return BASELINE_DIR / region / SEASON / f"{SEASON}-{region}-resi{level}_{suffix}.json"

    def _assert_timestamps_match(self, actual_path: str, baseline_path: Path):
        actual = load_json(actual_path)
        baseline = load_json(str(baseline_path))
        self.assertEqual(actual, baseline, f"Timestamps mismatch: {actual_path}")

    def _assert_edges_match(self, actual_path: str, baseline_path: Path):
        actual = normalize_edges(load_json(actual_path))
        baseline = normalize_edges(load_json(str(baseline_path)))

        missing = baseline - actual
        extra = actual - baseline

        self.assertEqual(
            actual, baseline,
            f"Edge mismatch in {actual_path}:\n"
            f"  Missing {len(missing)} edges\n"
            f"  Extra {len(extra)} edges"
        )


def _make_test(region, key_level):
    """Factory that creates a test method for a specific region + key_level."""

    def test_method(self):
        db_path = DB_DIR / f"{SEASON}-{region}.db"
        if not db_path.exists():
            self.skipTest(f"DB not found: {db_path}")

        results = run_analysis_for(region, SEASON, key_level)

        if results is None:
            # No resilient characters at this level — baseline should not exist either
            baseline_ts = self._baseline_path(region, key_level, "timestamps")
            self.assertFalse(
                baseline_ts.exists(),
                f"Analysis returned None but baseline exists: {baseline_ts}"
            )
            return

        # Compare timestamps
        self._assert_timestamps_match(
            results["timestamps_file"],
            self._baseline_path(region, key_level, "timestamps"),
        )

        # Compare resilient edges
        self._assert_edges_match(
            results["down_edges_file"],
            self._baseline_path(region, key_level, "down_edges"),
        )

        # Compare non-resilient edges
        self._assert_edges_match(
            results["non_resil_edges_file"],
            self._baseline_path(region, key_level, "non_resil_edges"),
        )

    test_method.__doc__ = f"Regression: {region} resi{key_level}"
    return test_method


# Dynamically generate one test per (region, key_level)
for _region in REGIONS:
    for _level in KEY_LEVELS:
        method_name = f"test_{_region}_resi{_level}"
        setattr(TestRegression, method_name, _make_test(_region, _level))


if __name__ == "__main__":
    unittest.main()