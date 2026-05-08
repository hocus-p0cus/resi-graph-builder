import json
import re
import sys
from pathlib import Path

REGIONS = ["eu", "na"]
TIMESTAMP_PATTERN = re.compile(r"resi(\d+)_timestamps\.json$")


def get_key_levels(season_dir: Path) -> list[int]:
    levels: set[int] = set()
    for f in season_dir.glob("*_timestamps.json"):
        m = TIMESTAMP_PATTERN.search(f.name)
        if m:
            levels.add(int(m.group(1)))
    return sorted(levels, reverse=True)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <data_dir> <season>", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    season = sys.argv[2]

    if not data_dir.is_dir():
        print(f"Error: {data_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    config_path = data_dir / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        config = {"regions": REGIONS, "seasons": {}, "keyLevels": {}}

    config.setdefault("regions", REGIONS)
    config.setdefault("seasons", {})
    config.setdefault("keyLevels", {})

    for region in REGIONS:
        season_dir = data_dir / region / season

        # Add season to the region's list if not already there
        region_seasons = config["seasons"].setdefault(region, [])
        if season not in region_seasons:
            region_seasons.append(season)

        # Update key levels for this region-season
        key = f"{region}-{season}"
        if season_dir.is_dir():
            levels = get_key_levels(season_dir)
            if levels:
                config["keyLevels"][key] = levels
                print(f"{key}: {levels}")
            else:
                print(f"{key}: no timestamp files found")
        else:
            print(f"{key}: directory {season_dir} does not exist, skipping")

    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nUpdated {config_path}")


if __name__ == "__main__":
    main()