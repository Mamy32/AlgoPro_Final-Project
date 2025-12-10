# game.py - Core Game Engine (433 lines)
"""
Main game class implementing 3D perspective racing game.
Inherits from tk.Canvas and contains all game logic, rendering, and state management.
"""

import math
import random
import time
import tkinter as tk
import pygame

# Import configuration and module dependencies
from config import WINDOW_WIDTH, WINDOW_HEIGHT, DIFFICULTIES, asset_path, AVAILABLE_MUSICS
from audio_manager import AudioManager
from highscore import load_high_score, save_high_score


class GalaxyGame(tk.Canvas):
    """Main game class - inherits from tk.Canvas for rendering capabilities."""

    # Game constants (tunable parameters)
    V_NB_LINES = 8  # Number of vertical perspective lines
    V_LINES_SPACING = 0.4  # Spacing between vertical lines (relative to width)
    H_NB_LINES = 8  # Number of horizontal lines
    H_LINES_SPACING = 0.15  # Spacing between horizontal lines
    NB_TILES = 16  # Maximum visible track tiles

    # Ship dimensions (relative to window size)
    SHIP_WIDTH = 0.1  # Ship width = 10% of window
    SHIP_HEIGHT = 0.035  # Ship height = 3.5% of window
    SHIP_BASE_Y = 0.04  # Vertical position from bottom

    COLLISION_START_LOOP = 5  # Score before collisions activate (tutorial period)
    MAX_OBSTACLES = 6  # Maximum simultaneous obstacles (Object Pool size)

    # Jump mechanics
    JUMP_DURATION = 0.6  # Seconds jump is active
    JUMP_COOLDOWN = 0.3  # Delay before next jump possible

    def __init__(self, master: tk.Tk, **kwargs) -> None:
        """Initialize game canvas and all game systems."""
        super().__init__(master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                         bg="black", highlightthickness=0, **kwargs)
        self.pack(fill="both", expand=True)

        # Perspective reference points (vanishing point)
        self.perspective_point_x = WINDOW_WIDTH / 2  # Center X
        self.perspective_point_y = WINDOW_HEIGHT * 0.75  # 75% from top

        # Game object storage (tkinter canvas item IDs)
        self.vertical_lines: list[int] = []  # Vertical line canvas items
        self.horizontal_lines: list[int] = []  # Horizontal line items
        self.tiles: list[int] = []  # Track tile items
        self.tiles_coordinates: list[tuple[int, int]] = []  # Tile grid positions
        self.obstacles: list[int] = []  # Obstacle items
        self.obstacle_coords: list[tuple[int, int]] = []  # Obstacle positions

        # Game state variables
        self.current_offset_y = 0.0  # Vertical scroll offset
        self.current_y_loop = 0  # Score/distance counter
        self.current_speed_x = 0.0  # Horizontal movement speed
        self.current_offset_x = 0.0  # Horizontal offset

        # Ship rendering
        self.ship_item: int | None = None  # Canvas item ID for ship
        self.ship_coordinates: list[tuple[float, float]] = [(0, 0), (0, 0), (0, 0)]  # Triangle points

        # Game states
        self.state_game_over = False
        self.state_game_has_started = False
        self.paused = False
        self.pause_text_item: int | None = None
        self.allow_collisions = False  # Collisions disabled at start

        # Difficulty system
        self.difficulty = "Normal"
        self.speed_y_base = DIFFICULTIES[self.difficulty]["speed"]  # Vertical speed
        self.speed_x_base = DIFFICULTIES[self.difficulty]["speed_x"]  # Horizontal speed

        # Level progression
        self.level = 0  # Current level (0 = score < 100)
        self.level_text_item: int | None = None  # "LEVEL N" text display
        self.level_flash_item: int | None = None  # White flash effect

        # Score system (using tkinter variables for automatic UI updates)
        self.score_txt = tk.StringVar(value="SCORE: 0")
        self.high_score = load_high_score()  # Load from file
        self.best_score_txt = tk.StringVar(value=f"BEST: {self.high_score}")

        # Color management
        self.tile_colors = ["#aaaaaa", "#ffcc00", "#00ff99", "#00ccff", "#ff66cc", "#ff4444"]
        self.current_tile_color = self.tile_colors[0]  # Starting color (gray)
        self.current_ship_color = "#b300ff"  # Purple ship (constant)

        # Jump system state
        self.jump_active = False
        self.jump_timer = 0.0
        self.jump_cooldown_timer = 0.0

        # Timing for frame-rate independence
        self.last_time = time.perf_counter()

        # Audio system
        self.audio = AudioManager()

        # Initialize all game components
        self._load_background()  # Load optional background image
        self._init_vertical_lines()  # Create perspective grid
        self._init_horizontal_lines()
        self._init_tiles()  # Create track tiles
        self._init_ship()  # Create player ship
        self._init_obstacles()  # Create obstacle pool

        # Build UI components
        self._build_menu_overlay()  # Create menu interface

        # Score display labels (attached to tkinter variables)
        self.score_label = tk.Label(master, textvariable=self.score_txt,
                                    bg="black", fg="#00ffff", font=("Arial", 14, "bold"))
        self.score_label.place(x=20, y=10)

        self.best_score_label = tk.Label(master, textvariable=self.best_score_txt,
                                         bg="black", fg="#00ffff", font=("Arial", 14, "bold"))
        self.best_score_label.place(relx=1.0, x=-150, y=10)

        # Input binding - keyboard
        master.bind("<KeyPress-Left>", self._on_key_down)
        master.bind("<KeyPress-Right>", self._on_key_down)
        master.bind("<KeyRelease-Left>", self._on_key_up)
        master.bind("<KeyRelease-Right>", self._on_key_up)
        master.bind("<KeyPress-p>", self._on_key_down)  # Pause
        master.bind("<KeyPress-P>", self._on_key_down)
        master.bind("<KeyPress-space>", self._on_key_down)  # Jump

        # Input binding - mouse
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)

        # Start game loop (first frame after 0ms delay)
        self.after(0, self._game_loop)

        # Play menu background music
        self.audio.play_menu_music()

    # ------------------------------------------------------------------ #
    # BACKGROUND IMAGE
    # ------------------------------------------------------------------ #
    def _load_background(self) -> None:
        """Load and display background image if available."""
        try:
            from PIL import Image, ImageTk  # Optional dependency
            img = Image.open(asset_path("bg1.jpg"))
            img = img.resize((WINDOW_WIDTH, WINDOW_HEIGHT), Image.LANCZOS)  # High-quality resize
            self.bg_image = ImageTk.PhotoImage(img)
            self.bg_item = self.create_image(0, 0, image=self.bg_image, anchor="nw")
        except Exception:
            # Graceful degradation: continue without background
            self.bg_image = None
            self.bg_item = None

    # ------------------------------------------------------------------ #
    # MENU SYSTEM
    # ------------------------------------------------------------------ #
    def _build_menu_overlay(self) -> None:
        """Build the main menu interface with options."""
        # Main menu frame (centered overlay)
        self.menu_frame = tk.Frame(self.master, bg="#000000", bd=0)
        self.menu_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title label
        self.menu_title_label = tk.Label(self.menu_frame, text="G   A   L   A   X   Y",
                                         fg="#00ffff", bg="#000000", font=("Arial", 24, "bold"))
        self.menu_title_label.pack(pady=(0, 10))

        # High score display in menu
        self.best_menu_label = tk.Label(self.menu_frame, textvariable=self.best_score_txt,
                                        fg="#00ffff", bg="#000000", font=("Arial", 14, "bold"))
        self.best_menu_label.pack(pady=(0, 10))

        # Difficulty selection (radio buttons)
        diff_frame = tk.Frame(self.menu_frame, bg="#000000")
        diff_frame.pack(pady=(0, 10))

        tk.Label(diff_frame, text="Difficulty:", fg="#00ffff", bg="#000000",
                 font=("Arial", 12, "bold")).pack(side="left", padx=5)

        self.diff_var = tk.StringVar(value=self.difficulty)
        for name in ["Easy", "Normal", "Hard"]:
            rb = tk.Radiobutton(diff_frame, text=name, variable=self.diff_var, value=name,
                                indicatoron=False, width=7, fg="#000000",
                                bg="#00ffff" if name == "Normal" else "#555555",
                                selectcolor="#00ffff", activebackground="#33ffff",
                                activeforeground="#000000", font=("Arial", 10, "bold"),
                                command=self._on_difficulty_changed)
            rb.pack(side="left", padx=3)

        # Music selection (dropdown)
        music_frame = tk.Frame(self.menu_frame, bg="#000000")
        music_frame.pack(pady=(0, 10))

        tk.Label(music_frame, text="Music:", fg="#00ffff", bg="#000000",
                 font=("Arial", 12, "bold")).pack(side="left", padx=5)

        self.music_var = tk.StringVar(value=list(AVAILABLE_MUSICS.keys())[0])  # First track default
        self.music_menu = tk.OptionMenu(music_frame, self.music_var, *AVAILABLE_MUSICS.keys())
        self.music_menu.configure(bg="#00aaaa", fg="black", activebackground="#33ffff",
                                  activeforeground="black", highlightthickness=0,
                                  font=("Arial", 10, "bold"), width=22)
        self.music_menu.pack(side="left")

        # Start/Restart button
        self.menu_button = tk.Button(self.menu_frame, text="START", font=("Arial", 14, "bold"),
                                     fg="#000000", bg="#00ffff", activebackground="#33ffff",
                                     activeforeground="#000000", relief="flat",
                                     padx=20, pady=5, command=self.on_menu_button_pressed)
        self.menu_button.pack(pady=(0, 10))

        # Sound toggle button
        self.sound_button = tk.Button(self.menu_frame, text="Sound: ON",
                                      font=("Arial", 10, "bold"), fg="#000000", bg="#00ffff",
                                      activebackground="#33ffff", activeforeground="#000000",
                                      relief="flat", padx=10, pady=3,
                                      command=self._on_toggle_sound_clicked)
        self.sound_button.pack(pady=(0, 5))

        # Control hints
        self.pause_hint_label = tk.Label(self.menu_frame,
                                         text="Press 'P' to pause/resume\nPress SPACE to jump",
                                         fg="#888888", bg="#000000", font=("Arial", 10, "italic"))
        self.pause_hint_label.pack(pady=(5, 0))

    def _on_difficulty_changed(self) -> None:
        """Update game speed based on selected difficulty."""
        name = self.diff_var.get()
        self.difficulty = name
        settings = DIFFICULTIES.get(name, DIFFICULTIES["Normal"])  # Default to Normal
        self.speed_y_base = settings["speed"]
        self.speed_x_base = settings["speed_x"]

    def show_menu(self, title: str, button_text: str) -> None:
        """Display menu with custom title and button text."""
        self.menu_title_label.configure(text=title)
        self.menu_button.configure(text=button_text)
        self.menu_frame.place(relx=0.5, rely=0.5, anchor="center")

    def hide_menu(self) -> None:
        """Hide the menu overlay."""
        self.menu_frame.place_forget()

    def _on_toggle_sound_clicked(self) -> None:
        """Toggle global sound on/off and update button text."""
        enabled = self.audio.toggle_sound()
        self.sound_button.configure(text=f"Sound: {'ON' if enabled else 'OFF'}")

        # Restart appropriate music if sound re-enabled
        if enabled:
            if not self.state_game_has_started and not self.state_game_over:
                self.audio.play_menu_music()
            elif self.state_game_has_started and not self.state_game_over:
                self.audio.play_game_music()

    # ------------------------------------------------------------------ #
    # INITIALIZATION METHODS
    # ------------------------------------------------------------------ #
    def _init_vertical_lines(self) -> None:
        """Create vertical perspective grid lines."""
        for _ in range(self.V_NB_LINES):
            line = self.create_line(0, 0, 0, 0, fill="#888888", width=2)
            self.vertical_lines.append(line)

    def _init_horizontal_lines(self) -> None:
        """Create horizontal perspective grid lines."""
        for _ in range(self.H_NB_LINES):
            line = self.create_line(0, 0, 0, 0, fill="#666666", width=1)
            self.horizontal_lines.append(line)

    def _init_tiles(self) -> None:
        """Create track tile polygons (pre-allocated for performance)."""
        for _ in range(self.NB_TILES):
            tile = self.create_polygon(0, 0, 0, 0, 0, 0, 0, 0,
                                       fill=self.current_tile_color, outline="")
            self.tiles.append(tile)
        self._reset_tiles()  # Initialize tile positions

    def _reset_tiles(self) -> None:
        """Reset tile coordinates to starting track."""
        self.tiles_coordinates.clear()
        for i in range(5, 15):  # Create initial straight track
            self.tiles_coordinates.append((0, i))
        self._generate_tiles_coordinates()  # Generate more track

    def _init_ship(self) -> None:
        """Create the player's ship (triangle polygon)."""
        self.ship_item = self.create_polygon(0, 0, 0, 0, 0, 0,
                                             fill=self.current_ship_color, outline="")

    def _init_obstacles(self) -> None:
        """Pre-create obstacle objects using Object Pool pattern."""
        for _ in range(self.MAX_OBSTACLES):
            obs = self.create_polygon(0, 0, 0, 0, 0, 0, 0, 0, fill="#ff0000", outline="")
            self.obstacles.append(obs)
            self.obstacle_coords.append((-999, -999))  # Mark as inactive (off-screen)

    # ------------------------------------------------------------------ #
    # PERSPECTIVE TRANSFORMATION
    # ------------------------------------------------------------------ #
    def transform(self, x: float, y: float) -> tuple[int, int]:
        """Transform world coordinates to screen coordinates."""
        return self.transform_perspective(x, y)

    def transform_perspective(self, x: float, y: float) -> tuple[int, int]:
        """
        Apply 3D perspective transformation to 2D coordinates.
        Core algorithm creating depth illusion with exponential scaling.
        """
        # Linear Y scaling based on distance from vanishing point
        lin_y = y * self.perspective_point_y / WINDOW_HEIGHT

        # Clamp to perspective point (objects can't go beyond horizon)
        if lin_y > self.perspective_point_y:
            lin_y = self.perspective_point_y

        # Calculate differences from vanishing point
        diff_x = x - self.perspective_point_x
        diff_y = self.perspective_point_y - lin_y

        # Exponential perspective factor (creates realistic depth)
        factor_y = diff_y / self.perspective_point_y
        factor_y = math.pow(factor_y, 4)  # 4th power gives good depth

        # Apply perspective offset to X coordinate
        offset_x = diff_x * factor_y

        # Calculate transformed coordinates
        tr_x = self.perspective_point_x + offset_x
        tr_y = self.perspective_point_y - factor_y * self.perspective_point_y

        # Convert to tkinter coordinate system (origin at top-left)
        tr_y_tk = WINDOW_HEIGHT - tr_y

        return int(tr_x), int(tr_y_tk)

    def get_line_x_from_index(self, index: int) -> float:
        """Convert grid index to world X coordinate."""
        central_line_x = self.perspective_point_x
        spacing = self.V_LINES_SPACING * WINDOW_WIDTH
        offset = index - 0.5  # Center lines between grid cells
        return central_line_x + offset * spacing + self.current_offset_x

    def get_line_y_from_index(self, index: int) -> float:
        """Convert grid index to world Y coordinate."""
        spacing_y = self.H_LINES_SPACING * WINDOW_HEIGHT
        return index * spacing_y - self.current_offset_y

    def get_tile_coordinates(self, ti_x: int, ti_y: int) -> tuple[float, float]:
        """Get world coordinates for a tile at grid position (ti_x, ti_y)."""
        ti_y = ti_y - self.current_y_loop  # Adjust for vertical scrolling
        x = self.get_line_x_from_index(ti_x)
        y = self.get_line_y_from_index(ti_y)
        return x, y

    # ------------------------------------------------------------------ #
    # OBJECT UPDATES (Rendering)
    # ------------------------------------------------------------------ #
    def _update_vertical_lines(self) -> None:
        """Update vertical line positions based on perspective."""
        start_index = -int(self.V_NB_LINES / 2) + 1
        for i in range(start_index, start_index + self.V_NB_LINES):
            line_x = self.get_line_x_from_index(i)
            x1, y1 = self.transform(line_x, 0)  # Top point
            x2, y2 = self.transform(line_x, WINDOW_HEIGHT)  # Bottom point
            self.coords(self.vertical_lines[i - start_index], x1, y1, x2, y2)

    def _update_horizontal_lines(self) -> None:
        """Update horizontal line positions based on perspective."""
        start_index = -int(self.V_NB_LINES / 2) + 1
        end_index = start_index + self.V_NB_LINES - 1

        xmin = self.get_line_x_from_index(start_index)
        xmax = self.get_line_x_from_index(end_index)

        for i in range(self.H_NB_LINES):
            line_y = self.get_line_y_from_index(i)
            x1, y1 = self.transform(xmin, line_y)  # Left point
            x2, y2 = self.transform(xmax, line_y)  # Right point
            self.coords(self.horizontal_lines[i], x1, y1, x2, y2)

    def _update_tiles(self) -> None:
        """Update all visible track tile positions."""
        for i, tile in enumerate(self.tiles):
            if i >= len(self.tiles_coordinates):
                continue  # Tile not currently used

            ti_x, ti_y = self.tiles_coordinates[i]
            xmin, ymin = self.get_tile_coordinates(ti_x, ti_y)
            xmax, ymax = self.get_tile_coordinates(ti_x + 1, ti_y + 1)

            # Transform all four corners
            x1, y1 = self.transform(xmin, ymin)
            x2, y2 = self.transform(xmin, ymax)
            x3, y3 = self.transform(xmax, ymax)
            x4, y4 = self.transform(xmax, ymin)

            # Update canvas coordinates
            self.coords(tile, x1, y1, x2, y2, x3, y3, x4, y4)

    def _update_ship(self) -> None:
        """Update ship position and transformation."""
        # Calculate ship geometry (triangle)
        center_x = WINDOW_WIDTH / 2
        base_y = self.SHIP_BASE_Y * WINDOW_HEIGHT
        half_width = self.SHIP_WIDTH * WINDOW_WIDTH / 2
        ship_height = self.SHIP_HEIGHT * WINDOW_HEIGHT

        # Set triangle vertices (left, bottom, right)
        self.ship_coordinates[0] = (center_x - half_width, base_y)  # Left
        self.ship_coordinates[1] = (center_x, base_y + ship_height)  # Bottom
        self.ship_coordinates[2] = (center_x + half_width, base_y)  # Right

        # Transform to screen coordinates
        x1, y1 = self.transform(*self.ship_coordinates[0])
        x2, y2 = self.transform(*self.ship_coordinates[1])
        x3, y3 = self.transform(*self.ship_coordinates[2])

        # Update canvas
        self.coords(self.ship_item, x1, y1, x2, y2, x3, y3)

    def _update_obstacles(self) -> None:
        """Update obstacle positions and visibility."""
        for i, (ti_x, ti_y) in enumerate(self.obstacle_coords):
            if ti_x == -999:  # Obstacle inactive
                self.coords(self.obstacles[i], 0, 0, 0, 0, 0, 0, 0, 0)  # Hide
                continue

            if ti_y < self.current_y_loop - 1:  # Obstacle passed
                self.obstacle_coords[i] = (-999, -999)  # Return to pool
                self.coords(self.obstacles[i], 0, 0, 0, 0, 0, 0, 0, 0)
                continue

            # Calculate obstacle bounds
            xmin, ymin = self.get_tile_coordinates(ti_x, ti_y)
            xmax, ymax = self.get_tile_coordinates(ti_x + 1, ti_y + 1)

            # Transform corners
            x1, y1 = self.transform(xmin, ymin)
            x2, y2 = self.transform(xmin, ymax)
            x3, y3 = self.transform(xmax, ymax)
            x4, y4 = self.transform(xmax, ymin)

            # Update and ensure obstacle is above track
            self.coords(self.obstacles[i], x1, y1, x2, y2, x3, y3, x4, y4)
            self.tag_raise(self.obstacles[i])  # Draw above track

    # ------------------------------------------------------------------ #
    # TRACK / OBSTACLES / COLORS / SPEED
    # ------------------------------------------------------------------ #
    def _generate_tiles_coordinates(self) -> None:
        """Procedurally generate new track segments."""
        # Remove tiles that have scrolled off screen
        for i in range(len(self.tiles_coordinates) - 1, -1, -1):
            if self.tiles_coordinates[i][1] < self.current_y_loop:
                del self.tiles_coordinates[i]

        # Get last tile position for continuation
        if len(self.tiles_coordinates) > 0:
            last_coordinate = self.tiles_coordinates[-1]
            last_x = last_coordinate[0]
            last_y = last_coordinate[1] + 1
        else:
            last_x, last_y = 0, 5

        # Generate new tiles to fill visible area
        for _ in range(len(self.tiles_coordinates), self.NB_TILES):
            r = random.randint(0, 2)  # 0=straight, 1=right, 2=left
            start_index = -int(self.V_NB_LINES / 2) + 1
            end_index = start_index + self.V_NB_LINES - 1

            # Prevent going off track edges
            if last_x <= start_index:
                r = 1  # Force right turn
            if last_x >= end_index:
                r = 2  # Force left turn

            # Place tile and generate path
            self.tiles_coordinates.append((last_x, last_y))

            if r == 1:  # Turn right
                last_x += 1
                self.tiles_coordinates.append((last_x, last_y))
                last_y += 1
                self.tiles_coordinates.append((last_x, last_y))
            elif r == 2:  # Turn left
                last_x -= 1
                self.tiles_coordinates.append((last_x, last_y))
                last_y += 1
                self.tiles_coordinates.append((last_x, last_y))

            last_y += 1

        # Possibly spawn an obstacle
        self._maybe_spawn_obstacle()

    def _update_tile_color_by_score(self) -> None:
        """Change track color based on score and trigger level changes."""
        band = self.current_y_loop // 100  # Every 100 points = new band

        # Update track color (cycles through palette)
        idx = band % len(self.tile_colors)
        self.current_tile_color = self.tile_colors[idx]
        for tile in self.tiles:
            self.itemconfigure(tile, fill=self.current_tile_color)

        # Level change event
        if band > 0 and band != self.level:
            self._on_level_changed(band)
            self.level = band

    def _on_level_changed(self, band: int) -> None:
        """Handle level up: visual effects + speed increase."""
        level_number = band + 1  # band=1 => LEVEL 2

        # Display "LEVEL N" text
        if self.level_text_item is None:
            self.level_text_item = self.create_text(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 40,
                                                    text="", fill="#00ffff",
                                                    font=("Arial", 24, "bold"))
        self.itemconfigure(self.level_text_item, text=f"LEVEL {level_number}",
                           fill="#00ffff", state="normal")

        # White flash effect
        if self.level_flash_item is None:
            self.level_flash_item = self.create_rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                                          fill="white", outline="")
        else:
            self.coords(self.level_flash_item, 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
            self.itemconfigure(self.level_flash_item, state="normal")

        # Ensure effects are above other elements
        self.tag_raise(self.level_flash_item)
        self.tag_raise(self.level_text_item)

        # Animate disappearance
        self.after(150, lambda: self.itemconfigure(self.level_flash_item, state="hidden"))
        self.after(1000, lambda: self.itemconfigure(self.level_text_item, state="hidden"))

        # Exponential speed increase (8% per level)
        base = DIFFICULTIES[self.difficulty]
        factor = 1.08 ** band
        self.speed_y_base = base["speed"] * factor
        self.speed_x_base = base["speed_x"] * factor

        # Keep ship purple (override any color changes)
        if self.ship_item is not None:
            self.itemconfigure(self.ship_item, fill=self.current_ship_color, outline="")

    def _maybe_spawn_obstacle(self) -> None:
        """Spawn obstacles with probability based on level."""
        if self.level < 1:
            return  # No obstacles in level 1 (score < 100)

        # Probability increases with level (caps at 70%)
        prob = min(0.3 + 0.1 * self.level, 0.7)
        if random.random() > prob:
            return

        # Group tiles by Y coordinate (row)
        rows: dict[int, set[int]] = {}
        for x, y in self.tiles_coordinates:
            if y <= self.current_y_loop + 1:  # Don't spawn too close to player
                continue
            rows.setdefault(y, set()).add(x)

        # Only spawn on rows with at least 2 paths (ensures player can avoid)
        candidates = [(y, xs) for (y, xs) in rows.items() if len(xs) >= 2]
        if not candidates:
            return

        # Choose random row and position
        row_y, xs = random.choice(candidates)
        ti_x = random.choice(list(xs))
        ti_y = row_y

        # Find available obstacle slot
        try:
            idx = self.obstacle_coords.index((-999, -999))
        except ValueError:
            return  # All obstacle slots occupied

        # Place obstacle
        self.obstacle_coords[idx] = (ti_x, ti_y)

    # ------------------------------------------------------------------ #
    # COLLISION DETECTION
    # ------------------------------------------------------------------ #
    def _check_ship_collision_with_tile(self, ti_x: int, ti_y: int) -> bool:
        """Check if ship polygon intersects with a specific tile."""
        xmin, ymin = self.get_tile_coordinates(ti_x, ti_y)
        xmax, ymax = self.get_tile_coordinates(ti_x + 1, ti_y + 1)

        # Check each ship vertex against tile bounds
        for px, py in self.ship_coordinates:
            if xmin <= px <= xmax and ymin <= py <= ymax:
                return True  # Collision detected
        return False

    def _check_ship_collisions(self) -> bool:
        """Check if ship has collided with track edges."""
        if not self.allow_collisions:
            return False  # Collisions disabled during early game

        safe = False
        # Only check tiles near the ship
        for ti_x, ti_y in self.tiles_coordinates:
            if ti_y < self.current_y_loop - 1:  # Too far behind
                continue
            if ti_y > self.current_y_loop + 2:  # Too far ahead
                continue
            if self._check_ship_collision_with_tile(ti_x, ti_y):
                safe = True
                break

        return not safe  # Collision if no tile under ship

    def _check_obstacle_collision(self) -> bool:
        """Check if ship has collided with red obstacles."""
        if self.level < 1:  # No obstacles in level 1
            return False
        if self.jump_active:  # Jumping avoids obstacles
            return False

        # Check all active obstacles near ship
        for ti_x, ti_y in self.obstacle_coords:
            if ti_x == -999:  # Inactive
                continue
            if ti_y < self.current_y_loop - 1 or ti_y > self.current_y_loop + 2:
                continue  # Too far away
            if self._check_ship_collision_with_tile(ti_x, ti_y):
                return True  # Obstacle collision
        return False

    # ------------------------------------------------------------------ #
    # INPUT & JUMP SYSTEM
    # ------------------------------------------------------------------ #
    def _try_jump(self) -> None:
        """Activate jump if conditions allow."""
        if (not self.state_game_has_started or self.state_game_over or self.paused):
            return
        if self.jump_active:  # Already jumping
            return
        if self.jump_cooldown_timer > 0:  # Cooldown active
            return

        # Activate jump
        self.jump_active = True
        self.jump_timer = self.JUMP_DURATION
        self.jump_cooldown_timer = self.JUMP_DURATION + self.JUMP_COOLDOWN

        # Visual feedback: white outline
        if self.ship_item is not None:
            self.itemconfigure(self.ship_item, fill=self.current_ship_color,
                               outline="#ffffff", width=2)

    def _update_jump_timers(self, dt: float) -> None:
        """Update jump and cooldown timers based on real time."""
        if self.jump_active:
            self.jump_timer -= dt
            if self.jump_timer <= 0:
                self.jump_active = False
                # Restore normal ship appearance
                if self.ship_item is not None:
                    self.itemconfigure(self.ship_item, fill=self.current_ship_color,
                                       outline="")

        if self.jump_cooldown_timer > 0:
            self.jump_cooldown_timer -= dt
            if self.jump_cooldown_timer < 0:
                self.jump_cooldown_timer = 0.0

    def _on_key_down(self, event) -> None:
        """Handle key press events."""
        if event.keysym == "Left":
            self.current_speed_x = self.speed_x_base  # Move left
        elif event.keysym == "Right":
            self.current_speed_x = -self.speed_x_base  # Move right
        elif event.keysym.lower() == "p":
            self._toggle_pause()  # Pause/unpause
        elif event.keysym == "space":
            self._try_jump()  # Jump

    def _on_key_up(self, event) -> None:
        """Handle key release events."""
        if event.keysym in ("Left", "Right"):
            self.current_speed_x = 0  # Stop horizontal movement

    def _on_mouse_down(self, event) -> None:
        """Handle mouse click events for movement."""
        if (not self.state_game_over and self.state_game_has_started and not self.paused):
            if event.x < WINDOW_WIDTH / 2:  # Click left half
                self.current_speed_x = self.speed_x_base  # Move left
            else:  # Click right half
                self.current_speed_x = -self.speed_x_base  # Move right

    def _on_mouse_up(self, event) -> None:
        """Handle mouse release events."""
        self.current_speed_x = 0  # Stop movement

    def _toggle_pause(self) -> None:
        """Toggle game pause state."""
        if not self.state_game_has_started or self.state_game_over:
            return

        self.paused = not self.paused

        if self.paused:
            # Show pause text
            if self.pause_text_item is None:
                self.pause_text_item = self.create_text(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2,
                                                        text="PAUSED", fill="#00ffff",
                                                        font=("Arial", 24, "bold"))
            else:
                self.itemconfigure(self.pause_text_item, state="normal")
        else:
            # Hide pause text
            if self.pause_text_item is not None:
                self.itemconfigure(self.pause_text_item, state="hidden")

    # ------------------------------------------------------------------ #
    # STATES / RESET / GAME LOOP
    # ------------------------------------------------------------------ #
    def reset_game(self) -> None:
        """Reset all game state to initial conditions."""
        self.current_offset_y = 0.0
        self.current_y_loop = 0
        self.current_speed_x = 0.0
        self.current_offset_x = 0.0
        self.tiles_coordinates = []
        self.score_txt.set("SCORE: 0")
        self.allow_collisions = False
        self.paused = False
        self.level = 0

        # Reset jump system
        self.jump_active = False
        self.jump_timer = 0.0
        self.jump_cooldown_timer = 0.0

        # Hide pause text if visible
        if self.pause_text_item is not None:
            self.itemconfigure(self.pause_text_item, state="hidden")

        # Reset colors
        self.current_tile_color = self.tile_colors[0]
        self.current_ship_color = "#b300ff"
        if self.ship_item is not None:
            self.itemconfigure(self.ship_item, fill=self.current_ship_color, outline="")

        # Reset obstacles (return all to pool)
        for i in range(self.MAX_OBSTACLES):
            self.obstacle_coords[i] = (-999, -999)
            self.coords(self.obstacles[i], 0, 0, 0, 0, 0, 0, 0, 0)

        # Reset track
        self._reset_tiles()
        self.state_game_over = False

    def on_menu_button_pressed(self) -> None:
        """Handle menu button press (Start or Restart)."""
        if self.state_game_over:
            self.audio.play_sfx(self.audio.snd_restart)
        else:
            self.audio.play_sfx(self.audio.snd_begin)

        # Apply selected difficulty
        self._on_difficulty_changed()

        # Set selected music
        selected_music = self.music_var.get()
        filename = AVAILABLE_MUSICS.get(selected_music)
        if filename:
            self.audio.set_music(filename)

        # Reset and start game
        self.reset_game()
        self.state_game_has_started = True
        self.state_game_over = False

        # Transition to gameplay
        self.hide_menu()
        self.audio.stop_menu_music()
        self.audio.play_game_music()

    def _on_game_over(self) -> None:
        """Handle game over sequence."""
        self.state_game_over = True
        self.state_game_has_started = False

        # Update high score if beaten
        if self.current_y_loop > self.high_score:
            self.high_score = self.current_y_loop
            self.best_score_txt.set(f"BEST: {self.high_score}")
            save_high_score(self.high_score)

        # Show game over menu
        self.show_menu("G  A  M  E    O  V  E  R", "RESTART")

        # Audio effects
        self.audio.stop_game_music()
        self.audio.play_sfx(self.audio.snd_gameover_impact)
        self.audio.play_sfx(self.audio.snd_gameover_voice)

        # Return to menu music after delay
        self.after(2000, self.audio.play_menu_music)

    def _game_loop(self) -> None:
        """Main game loop - runs approximately 60 times per second."""
        # Calculate delta time (frame-rate independence)
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now
        time_factor = dt * 60.0  # Normalize to target 60 FPS

        # Update jump timers (real-time based)
        self._update_jump_timers(dt)

        # Update all visual elements
        self._update_vertical_lines()
        self._update_horizontal_lines()
        self._update_tiles()
        self._update_obstacles()
        self._update_ship()

        # Game logic only when playing (not paused/game over)
        if (not self.state_game_over and self.state_game_has_started and not self.paused):
            # Vertical movement (forward progress)
            speed_y = self.speed_y_base * WINDOW_HEIGHT / 100.0
            self.current_offset_y += speed_y * time_factor

            # Score increment when passing horizontal line
            spacing_y = self.H_LINES_SPACING * WINDOW_HEIGHT
            while self.current_offset_y >= spacing_y:
                self.current_offset_y -= spacing_y
                self.current_y_loop += 1
                self.score_txt.set(f"SCORE: {self.current_y_loop}")

                # Update colors and check for level up
                self._update_tile_color_by_score()

                # Generate new track segments
                self._generate_tiles_coordinates()

                # Enable collisions after initial safe period
                if (not self.allow_collisions and
                        self.current_y_loop >= self.COLLISION_START_LOOP):
                    self.allow_collisions = True

            # Horizontal movement (player control)
            speed_x = self.current_speed_x * WINDOW_WIDTH / 100.0
            self.current_offset_x += speed_x * time_factor

            # Check for collisions
            if self._check_ship_collisions() or self._check_obstacle_collision():
                self._on_game_over()

        # Schedule next frame (~60 FPS = 16ms delay)
        self.after(16, self._game_loop)