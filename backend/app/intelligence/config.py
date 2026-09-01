"""Canonical configuration and path resolution for SAT-SA Threat Intelligence."""
import os


def get_data_dir() -> str:
    """Returns the canonical absolute path to the repository data/ directory."""
    root_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
    if os.path.exists(root_data) and os.path.isdir(root_data):
        return root_data
    if os.path.exists("data") and os.path.isdir("data"):
        return os.path.abspath("data")
    os.makedirs(root_data, exist_ok=True)
    return root_data

