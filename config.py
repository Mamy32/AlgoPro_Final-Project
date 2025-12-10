# config.py
import os

# Dossiers de base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.txt")

# Dimensions of the window
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 800

# Difficulty of the game
DIFFICULTIES = {
    "Easy": {"speed": 0.6, "speed_x": 2.5},
    "Normal": {"speed": 0.8, "speed_x": 3.5},
    "Hard": {"speed": 1.1, "speed_x": 4.5},
}


def asset_path(name: str) -> str:
    """path to the image, ex: bg1.jpg."""
    return os.path.join(BASE_DIR, name)


def audio_path(name: str) -> str:
    """path to the audio/."""
    return os.path.join(AUDIO_DIR, name)


AVAILABLE_MUSICS = {
    # music originale
    "Level 1 (Original)": "music1.wav",
    # instrumental dancehall (.mp3)
    "DH – Bang 2020": "best-reddim.mp3",
    "DH – Chi Chi Pop": "Afro Type Beat Chi Chi Pop_Dancehall Latino Instrumental 2019.mp3",
    "DH – Drive Shatta": "DANCEHALL_Instrumental__🚲__DRIVE__Shatta_x_Moombahton_type_beat(128k).mp3",
    "DH – Hold On 2025": "Dancehall_Riddim_Instrumental_2025__Hold_On_(128k).mp3",
}
