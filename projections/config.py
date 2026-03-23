import os
from pathlib import Path

# Allow overriding via env var; fall back to local data dir
_default_data_dir = Path(__file__).resolve().parent / "data"
DATA_DIR = Path(os.environ.get("PROJECTION_DATA_DIR", _default_data_dir))

KENPOM_RATINGS_PATH = DATA_DIR / "kenpom2026_after_first_weekend.tsv"
SILVER_RATINGS_PATH = DATA_DIR / "silver_after_first_weekend.csv"
MATCHUP_TREE_PATH = DATA_DIR / "matchup_tree_silver.csv"
TEAM_NAME_MAPPING_PATH = DATA_DIR / "team_name_mapping.csv"
PLAYER_DATA_PATH = DATA_DIR / "player_data_2026_with_distributions_recency.pkl"
TEAM_RATINGS_PATH = DATA_DIR / "team_ratings_2026.pkl"

DEFAULT_N_SIMS = 10000
DEFAULT_CADENCE_MINUTES = 90
