# main.py - Application Entry Point
"""
Main entry point for Galaxy Game.
Initializes window and starts the game.
"""

import tkinter as tk  # GUI framework
import pygame  # Audio management

from config import WINDOW_WIDTH, WINDOW_HEIGHT  # Window size constants
from game import GalaxyGame  # Main game class


def main() -> None:
    """Create window, initialize game, and start event loop."""

    # Create main window
    root = tk.Tk()
    root.title("Galaxy (Tkinter OOP)")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.resizable(False, False)  # Fixed window size
    root.configure(bg="black")  # Black background

    # Create game instance
    game = GalaxyGame(root)
    game.show_menu("G   A   L   A   X   Y", "START")  # Show main menu

    def on_close():
        """Clean up audio resources before closing."""
        try:
            pygame.mixer.quit()  # Stop pygame audio
        except Exception:
            pass  # Graceful failure
        root.destroy()  # Close window

    # Set cleanup handler for window close
    root.protocol("WM_DELETE_WINDOW", on_close)

    # Start the GUI event loop
    root.mainloop()


if __name__ == "__main__":
    main()  # Run application