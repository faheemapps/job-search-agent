"""Loads candidate_profile.yaml and job_search_config.yaml."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def load_profile(path=None):
    path = path or CONFIG_DIR / "candidate_profile.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_search_config(path=None):
    path = path or CONFIG_DIR / "job_search_config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)
