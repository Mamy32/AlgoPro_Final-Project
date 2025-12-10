# audio_manager.py - Audio Management System
"""
Manages all game audio using pygame.mixer.
Handles sound effects, background music, and volume control.
"""

import os
import pygame  # Audio library
from config import audio_path  # Helper function for audio file paths


class AudioManager:
    """Manages all game sounds and music via pygame.mixer."""

    def __init__(self) -> None:
        """Initialize audio system and load sound assets."""
        self.sound_enabled: bool = True  # Global sound on/off toggle

        # Initialize pygame audio mixer with professional settings
        try:
            # 44.1kHz, 16-bit, stereo, optimized buffer
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass  # Silently fail if audio already initialized or unavailable

        # Load all sound effects
        self.snd_begin = self._load_sound("begin.wav")  # Game start sound
        self.snd_galaxy = self._load_sound("galaxy.wav")  # Menu music
        self.snd_gameover_impact = self._load_sound("gameover_impact.wav")  # Collision
        self.snd_gameover_voice = self._load_sound("gameover_voice.wav")  # "Game Over"
        self.snd_restart = self._load_sound("restart.wav")  # Restart sound

        # Default game music
        self.music_file = audio_path("music1.wav")

    def _load_sound(self, filename: str):
        """Load a sound file, return None if file missing or invalid."""
        path = audio_path(filename)
        if not os.path.exists(path):  # Check file exists
            return None
        try:
            return pygame.mixer.Sound(path)  # Load sound into memory
        except Exception:
            return None  # Return None if loading fails

    # --------- Sound Effects --------- #
    def play_sfx(self, snd) -> None:
        """Play a sound effect if sound is enabled."""
        if not self.sound_enabled or snd is None:
            return
        snd.play()  # Non-blocking playback

    # --------- Menu Music --------- #
    def play_menu_music(self) -> None:
        """Play looping menu background music."""
        if not self.sound_enabled:
            return
        if self.snd_galaxy is not None:
            self.snd_galaxy.play(loops=-1)  # -1 = infinite loop

    def stop_menu_music(self) -> None:
        """Stop menu music playback."""
        if self.snd_galaxy is not None:
            self.snd_galaxy.stop()

    # --------- Game Music --------- #
    def set_music(self, filename: str) -> None:
        """Set current game music from audio filename."""
        full = audio_path(filename)
        if not os.path.exists(full):
            return
        self.music_file = full  # Store path for later playback

    def play_game_music(self) -> None:
        """Play background music for gameplay."""
        if not self.sound_enabled:
            return
        if os.path.exists(self.music_file):
            try:
                pygame.mixer.music.load(self.music_file)  # Load music file
                pygame.mixer.music.set_volume(0.7)  # 70% volume
                pygame.mixer.music.play(-1)  # Loop indefinitely
            except Exception:
                pass  # Silent failure if music can't play

    def stop_game_music(self) -> None:
        """Stop all game music playback."""
        pygame.mixer.music.stop()

    # --------- Global Sound Control --------- #
    def toggle_sound(self) -> bool:
        """
        Toggle sound on/off globally.

        Returns:
            bool: True if sound is enabled after toggle, False if disabled.
        """
        self.sound_enabled = not self.sound_enabled

        # If disabling sound, stop all audio
        if not self.sound_enabled:
            self.stop_menu_music()
            self.stop_game_music()

        return self.sound_enabled  # Return new state