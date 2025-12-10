# highscore.py - Score Persistence Module
"""
Handles saving and loading of high scores to/from file.
Simple file-based persistence system.
"""

from config import HIGHSCORE_FILE  # Path to score file: "highscore.txt"


def load_high_score() -> int:
    """
    Load the high score from file.
    Returns:
        int: The saved high score, or 0 if file doesn't exist/corrupted.
    """
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            val = int(f.read().strip())  # Read, strip whitespace, convert to int
            return max(0, val)  # Ensure non-negative score
    except Exception:
        return 0  # Default if file missing or corrupted


def save_high_score(value: int) -> None:
    """
    Save a new high score to file.
    Args:
        value (int): The score to save (negative values handled as 0)
    """
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(int(value)))  # Convert to int, then string for writing
    except Exception:
        pass  # Silent failure - game continues without saving