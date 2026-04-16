"""
game.py  —  NEON SERPENT: Arcade Edition
Main game loop, mode logic, integration of all subsystems.

Run:  python game.py
"""

import pygame
import sys
import math
import random
import time
from typing import Optional, List, Dict, Any

# ── Local modules ────────────────────────────────────────────────────────────
from snake       import Snake, SKINS
from food        import MultiFood, FOOD_TYPES
from particles   import ParticleSystem
from powerups    import PowerUpManager, POWERUP_TYPES
from effects     import ScreenShake, SlowMotion, ScreenFlash, Vignette, ScanLines, DangerPulse, FogLayer
from sound_manager import SoundManager
from ui          import (MainMenu, HUD, GameOverScreen, PauseOverlay,
                         LevelUpOverlay, AchievementToast, SettingsPanel,
                         AnimatedBackground, draw_text_shadow, PAL, draw_neon_rect)
from progression import ProgressionManager, ComboSystem, ACHIEVEMENTS

# ── Constants ────────────────────────────────────────────────────────────────
CELL = 28
COLS = 40
ROWS = 28
W    = CELL * COLS   # 1120
H    = CELL * ROWS   # 784
FPS  = 60

# ── Level themes (game levels, not player levels) ────────────────────────────
LEVEL_THEMES = {
    1: {"name": "CYBER GRID",       "bg": (4, 6, 14),   "accent": (80, 255, 160),  "fog": False},
    2: {"name": "NEON DISTRICT",    "bg": (6, 4, 18),   "accent": (180, 80, 255),  "fog": False},
    3: {"name": "ACID RAIN",        "bg": (4, 14, 6),   "accent": (120, 255, 50),  "fog": True},
    4: {"name": "BLOOD CIRCUIT",    "bg": (18, 4, 4),   "accent": (255, 60, 80),   "fog": True},
    5: {"name": "VOID DIMENSION",   "bg": (2, 2, 16),   "accent": (80, 120, 255),  "fog": True},
    6: {"name": "INFERNO CORE",     "bg": (20, 6, 0),   "accent": (255, 120, 30),  "fog": True},
    7: {"name": "SINGULARITY",      "bg": (0, 0, 0),    "accent": (255, 255, 255), "fog": True},
}

SCORE_THRESHOLDS = [0, 80, 200, 380, 620, 940, 1400]  # score to reach each level

DIFFICULTY_CONFIG = {
    # move_ms = milliseconds between each snake step (higher = slower snake)
    # EASY: 1 move per 160ms (~6/sec), MEDIUM: 110ms (~9/sec), HARD: 75ms (~13/sec)
    "EASY":   {"move_ms": 160, "score_mult": 1, "obstacles": 0,  "powerup_cd": 360, "wrap": True},
    "MEDIUM": {"move_ms": 110, "score_mult": 2, "obstacles": 3,  "powerup_cd": 300, "wrap": False},
    "HARD":   {"move_ms":  75, "score_mult": 3, "obstacles": 6,  "powerup_cd": 240, "wrap": False},
}

MODE_TIMERS = {
    "TIME ATTACK": 90.0,
    "CHALLENGE":   None,
    "CLASSIC":     None,
    "SURVIVAL":    None,
}


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def clamp_col(c):
    return tuple(max(0, min(255, int(v))) for v in c)


# ── Font loader ───────────────────────────────────────────────────────────────

def load_fonts() -> dict:
    candidates = ["georgia", "palatino", "times new roman", "garamond",
                  "bookman", "constantia", None]
    def best_font(size, bold=False):
        for name in candidates:
            try:
                if name is None:
                    return pygame.font.Font(None, size)
                f = pygame.font.SysFont(name, size, bold=bold)
                return f
            except Exception:
                continue
        return pygame.font.Font(None, size)

    return {
        "title":    best_font(82, bold=True),
        "title_sm": best_font(58, bold=True),
        "subtitle": best_font(32, bold=True),
        "score":    best_font(38, bold=True),
        "med":      best_font(26, bold=True),
        "sm":       best_font(20, bold=False),
        "tiny":     best_font(16),
        "icon":     best_font(28),
        "powerup":  best_font(22),
        "combo":    best_font(44, bold=True),
        "timer":    best_font(50, bold=True),
    }


# ── Obstacles ────────────────────────────────────────────────────────────────

class Obstacle:
    def __init__(self, gx, gy, kind="wall"):
        self.gx   = gx
        self.gy   = gy
        self.kind = kind
        self._tick = 0

    @property
    def pos(self):
        return (self.gx, self.gy)

    def draw(self, surf, tick, accent_col):
        self._tick = tick
        cx = self.gx * CELL + CELL // 2
        cy = self.gy * CELL + CELL // 2
        pulse = (math.sin(tick * 0.08 + self.gx * 0.5) + 1) / 2

        col = (180, 80, 80)
        pygame.draw.rect(surf, col,
                         (self.gx * CELL + 2, self.gy * CELL + 2, CELL - 4, CELL - 4),
                         border_radius=4)
        # Glow
        ga = int(60 * pulse)
        gs = pygame.Surface((CELL + 8, CELL + 8), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*col, ga), (0, 0, CELL + 8, CELL + 8), border_radius=6)
        surf.blit(gs, (self.gx * CELL - 4, self.gy * CELL - 4))
        # X mark
        pygame.draw.line(surf, (255, 200, 200),
                         (self.gx * CELL + 5, self.gy * CELL + 5),
                         (self.gx * CELL + CELL - 5, self.gy * CELL + CELL - 5), 2)
        pygame.draw.line(surf, (255, 200, 200),
                         (self.gx * CELL + CELL - 5, self.gy * CELL + 5),
                         (self.gx * CELL + 5, self.gy * CELL + CELL - 5), 2)


def spawn_obstacles(count: int, snake_body, food_positions) -> List[Obstacle]:
    occupied = set(snake_body) | set(food_positions)
    obstacles = []
    mid_x = COLS // 2
    mid_y = ROWS // 2
    # Keep center clear for snake start
    safe_zone = {(mid_x + dx, mid_y + dy) for dx in range(-4, 5) for dy in range(-4, 5)}
    for _ in range(count * 3):
        if len(obstacles) >= count:
            break
        gx = random.randint(1, COLS - 2)
        gy = random.randint(3, ROWS - 2)
        pos = (gx, gy)
        if pos not in occupied and pos not in safe_zone:
            obstacles.append(Obstacle(gx, gy))
            occupied.add(pos)
    return obstacles


# ── Game Session ─────────────────────────────────────────────────────────────

class GameSession:
    """One play session. Created fresh each game."""

    def __init__(self, mode: str, difficulty: str, skin_key: str, fonts: dict):
        self.mode       = mode
        self.difficulty = difficulty
        cfg             = DIFFICULTY_CONFIG[difficulty]

        self.snake      = Snake(skin_key)
        self.food       = MultiFood(max_food=2)
        self.particles  = ParticleSystem()
        self.powerups   = PowerUpManager()
        self.powerups._spawn_cd = 180  # first powerup after 3s

        self.combo      = ComboSystem()
        self.score      = 0
        self.level      = 1
        self.theme      = LEVEL_THEMES[1]
        self.tick       = 0
        self.move_timer = 0.0
        self.alive      = True

        # Stats for achievements / challenges
        self.stats: Dict[str, Any] = {
            "food_eaten":       0,
            "max_combo":        0,
            "max_length":       6,
            "score":            0,
            "level":            1,
            "time_alive":       0.0,
            "powerups_collected": 0,
            "shield_saves":     0,
            "xp_earned":        0,
            "difficulty":       difficulty,
            "mode":             mode,
        }

        # Mode-specific
        self.timer: Optional[float] = MODE_TIMERS.get(mode)
        self.survival_speed_bonus   = 0
        self.challenge_obstacles: List[Obstacle] = []
        self._challenge_level       = 1

        # Obstacles
        if mode == "CHALLENGE" or cfg["obstacles"] > 0:
            count = cfg["obstacles"]
            self.challenge_obstacles = spawn_obstacles(
                count, self.snake.body, self.food.positions)

        # Fonts ref (for floating text)
        self.fonts = fonts

    @property
    def move_interval_ms(self) -> float:
        """Returns milliseconds between snake steps. Lower = faster."""
        base = DIFFICULTY_CONFIG[self.difficulty]["move_ms"]
        # Survival: speed up by 10ms every 10 seconds, min 40ms
        survival_reduction = int(self.survival_speed_bonus) * 10
        # Powerups: SLOW doubles interval, SPEED halves it
        slow_mult = 2.2 if self.powerups.has("SLOW") else 1.0
        fast_mult = 0.6 if self.powerups.has("SPEED") else 1.0
        result = (base - survival_reduction) * slow_mult * fast_mult
        return max(40.0, result)  # never faster than 40ms (25 moves/sec)

    @property
    def score_mult(self) -> float:
        base  = DIFFICULTY_CONFIG[self.difficulty]["score_mult"]
        double = 2.0 if self.powerups.has("DOUBLE") else 1.0
        combo  = self.combo.multiplier
        return base * double * combo

    @property
    def wrap_walls(self) -> bool:
        return (DIFFICULTY_CONFIG[self.difficulty].get("wrap", False) or
                self.powerups.has("GHOST"))

    def update_level(self):
        new_level = 1
        for i, threshold in enumerate(SCORE_THRESHOLDS[1:], 2):
            if self.score >= threshold:
                new_level = i
        new_level = min(new_level, len(LEVEL_THEMES))
        if new_level != self.level:
            self.level = new_level
            self.theme = LEVEL_THEMES[new_level]
            self.stats["level"] = new_level
            return True
        return False

    def add_obstacle_wave(self):
        self._challenge_level += 1
        occ = self.snake.body + self.food.positions + [o.pos for o in self.challenge_obstacles]
        new_obs = spawn_obstacles(2, occ, self.food.positions)
        self.challenge_obstacles.extend(new_obs)


# ── Main Game Class ───────────────────────────────────────────────────────────

class NeonSerpentGame:
    STATE_MENU     = "menu"
    STATE_PLAYING  = "playing"
    STATE_PAUSED   = "paused"
    STATE_DEAD     = "dead"
    STATE_LEVELUP  = "levelup"
    STATE_SETTINGS = "settings"

    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self._real_w = info.current_w
        self._real_h = info.current_h

        pygame.display.set_caption("◈ NEON SERPENT ◈")
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.FULLSCREEN)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))

        self.clock   = pygame.time.Clock()
        self.fonts   = load_fonts()

        # Core systems
        self.sound   = SoundManager()
        self.prog    = ProgressionManager()
        self.bg      = AnimatedBackground()
        self.shake   = ScreenShake()
        self.flash   = ScreenFlash()
        self.vignette = Vignette()
        self.scanlines = ScanLines()
        self.fog     = FogLayer()
        self.danger  = DangerPulse()

        # Global surfaces
        self.game_surf = pygame.Surface((W, H))
        self._render_surf = pygame.Surface((W, H))

        # UI state
        self.state   = self.STATE_MENU
        self._menu   = MainMenu(self.fonts, self.prog.hi_scores, self.bg)
        self._hud    = HUD(self.fonts)
        self._pause  = PauseOverlay(self.fonts)
        self._game_over = None
        self._levelup   = None
        self._settings  = SettingsPanel(self.fonts, {
            "sfx_vol":   self.sound.sfx_vol,
            "music_vol": self.sound.music_vol,
            "particles": True,
            "shake":     True,
            "trail":     True,
        })
        self._toasts: List[AchievementToast] = []

        # Active session
        self.session: Optional[GameSession] = None
        self._current_skin = "default"

        # FPS tracking
        self._fps_timer   = 0.0
        self._fps_display = 60

        # Start menu music
        self.sound.start_music()

        self._tick = 0

    # ── Main Loop ────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._fps_timer += 1
            if self._fps_timer >= 30:
                self._fps_display = int(self.clock.get_fps())
                self._fps_timer = 0

            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()
        sys.exit()

    # ── Event handling ───────────────────────────────────────────────────────

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN:
                self._on_key(event.key)

    def _on_key(self, key):
        # Global keys
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        if key == pygame.K_m and self.state in (self.STATE_PLAYING, self.STATE_PAUSED):
            self.sound.toggle_music()
            return

        if self.state == self.STATE_MENU:
            if key == pygame.K_TAB:
                self._settings.toggle()
                return
            self._settings.handle_key(key)
            if self._settings.open:
                return
            result = self._menu.handle_key(key)
            if result:
                self.sound.play("menu_confirm")
                self._start_session(result["mode"], result["difficulty"])
            else:
                self.sound.play("menu_select")
            if key == pygame.K_ESCAPE:
                self._quit()

        elif self.state == self.STATE_PLAYING:
            sess = self.session
            if key in (pygame.K_w, pygame.K_UP):    sess.snake.set_direction((0, -1))
            elif key in (pygame.K_s, pygame.K_DOWN): sess.snake.set_direction((0,  1))
            elif key in (pygame.K_a, pygame.K_LEFT): sess.snake.set_direction((-1, 0))
            elif key in (pygame.K_d, pygame.K_RIGHT):sess.snake.set_direction((1,  0))
            elif key == pygame.K_p or key == pygame.K_ESCAPE:
                self.state = self.STATE_PAUSED
                self._pause = PauseOverlay(self.fonts)
            elif key == pygame.K_TAB:
                self._settings.toggle()

        elif self.state == self.STATE_PAUSED:
            self._settings.handle_key(key)
            if key in (pygame.K_p, pygame.K_RETURN) and not self._settings.open:
                self.state = self.STATE_PLAYING
            elif key == pygame.K_ESCAPE:
                if self._settings.open:
                    self._settings.open = False
                else:
                    self._return_to_menu()

        elif self.state == self.STATE_DEAD:
            if key == pygame.K_RETURN or key == pygame.K_SPACE:
                self.sound.play("menu_confirm")
                self._start_session(self.session.mode, self.session.difficulty)
            elif key == pygame.K_m or key == pygame.K_ESCAPE:
                self._return_to_menu()

        elif self.state == self.STATE_LEVELUP:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = self.STATE_PLAYING

    def _quit(self):
        self.prog.save()
        pygame.quit()
        sys.exit()

    def _return_to_menu(self):
        self.prog.save()
        self.state  = self.STATE_MENU
        self._menu  = MainMenu(self.fonts, self.prog.hi_scores, self.bg)
        self.sound.start_music()

    # ── Session start ────────────────────────────────────────────────────────

    def _start_session(self, mode: str, difficulty: str):
        self.session = GameSession(mode, difficulty, self._current_skin, self.fonts)
        self.shake   = ScreenShake()
        self.flash   = ScreenFlash()
        self.danger  = DangerPulse()
        self.state   = self.STATE_PLAYING
        self._toasts = []
        self._tick   = 0
        self.prog.record_game(mode, difficulty, {})
        self.sound.play("menu_confirm")

    # ── Update ───────────────────────────────────────────────────────────────

    def _update(self, dt: float):
        self._tick += 1

        # Apply settings
        sv = self._settings.values
        self.sound.set_sfx_volume(sv.get("sfx_vol", 0.7))
        self.sound.set_music_volume(sv.get("music_vol", 0.35))

        # Update effects
        self.shake.update()
        self.flash.update()
        self.danger.update()

        # Update toasts
        self._toasts = [t for t in self._toasts if not t.done]

        if self.state == self.STATE_MENU:
            return

        if self.state == self.STATE_LEVELUP:
            if self._levelup and not self._levelup.done:
                pass
            return

        if self.state != self.STATE_PLAYING:
            return

        sess = self.session

        # Update subsystems
        self._hud.update(sess.score)
        sess.combo.update()
        sess.particles.update()

        # Time modes
        if sess.mode == "TIME ATTACK" and sess.timer is not None:
            sess.timer -= dt / 1000.0
            if sess.timer <= 0:
                sess.timer = 0
                self._die(sess)
                return
            # Countdown beeps
            t = sess.timer
            if abs(t - int(t)) < 0.05 and t <= 10:
                self.sound.play("beep_lo" if t > 5 else "beep_hi")

        if sess.mode == "SURVIVAL":
            # Speed increases every 10 seconds
            elapsed = sess.stats["time_alive"]
            sess.survival_speed_bonus = int(elapsed // 10) * 1.5

        # Update stats timing
        sess.stats["time_alive"] += dt / 1000.0

        # Move snake  ── dt-based timing (frame-rate independent) ──────────
        # move_timer accumulates real milliseconds. When it exceeds
        # move_interval_ms, take one step and reset.
        sess.move_timer += dt
        if sess.move_timer >= sess.move_interval_ms:
            sess.move_timer -= sess.move_interval_ms   # keep remainder, don't lose time
            if sess.alive:
                self._step(sess)

        # Update food
        magnet = sess.powerups.has("MAGNET")
        sess.food.update(sess.snake.body, magnet)

        # Update powerup world
        sess.powerups.update(sess.snake.body, sess.food.positions)
        spawned = sess.powerups.try_spawn(
            sess.snake.body, sess.food.positions, COLS, ROWS)

        # Trail particles
        if sv.get("trail", True):
            sess.snake.draw_trail(self.game_surf, sess.particles, self._tick)

        # Danger pulse: near walls
        hx, hy = sess.snake.head
        near_wall = (hx <= 1 or hx >= COLS - 2 or hy <= 1 or hy >= ROWS - 2)
        self.danger.set_active(near_wall and not sess.powerups.has("GHOST"))

        # Daily challenge updates
        daily_results = []
        for key, val in [
            ("food_eaten",  sess.stats["food_eaten"]),
            ("score",       sess.score),
            ("max_combo",   sess.stats["max_combo"]),
            ("time_alive",  sess.stats["time_alive"]),
            ("level",       sess.level),
            ("max_length",  len(sess.snake.body)),
            ("powerups",    sess.stats["powerups_collected"]),
        ]:
            completed = self.prog.update_daily(key, val)
            daily_results.extend(completed)

        for ch in daily_results:
            self._toast(f"CHALLENGE: {ch['desc']}", f"+{ch['xp']} XP")

        # Skin unlocks
        new_skins = self.prog.check_skin_unlocks()
        for sk in new_skins:
            self._toast(f"SKIN UNLOCKED: {SKINS[sk]['name']}", "New look available!")

    def _step(self, sess: GameSession):
        """One snake move tick."""
        obstacle_set = {o.pos for o in sess.challenge_obstacles}
        head_before  = sess.snake.head

        moved = sess.snake.move(wrap=sess.session_wrap if hasattr(sess, 'session_wrap') else
                                     DIFFICULTY_CONFIG[sess.difficulty]["wrap"] or sess.powerups.has("GHOST"))
        if not moved:
            # Check shield
            if sess.powerups.has("SHIELD"):
                # Burn shield, revive at safe position
                sess.powerups.active = [e for e in sess.powerups.active if e.kind != "SHIELD"]
                sess.snake.alive = True
                sess.snake.body  = [(COLS // 2, ROWS // 2)] + sess.snake.body[1:]
                self.sound.play("shield_break")
                self.flash.trigger((80, 180, 255), 120, 20)
                self.shake.add(0.5)
                sess.stats["shield_saves"] += 1
                return
            self._die(sess)
            return

        new_head = sess.snake.head

        # Obstacle collision
        if new_head in obstacle_set:
            if sess.powerups.has("SHIELD"):
                sess.powerups.active = [e for e in sess.powerups.active if e.kind != "SHIELD"]
                sess.snake.alive     = True
                self.sound.play("shield_break")
                self.flash.trigger((80, 180, 255), 120, 20)
                sess.stats["shield_saves"] += 1
                # Push back
                sess.snake.body[0] = head_before
                return
            sess.snake.alive = False
            self._die(sess)
            return

        # Food check
        eaten, kind, base_score, grow = sess.food.check_eat(new_head)
        if eaten:
            self._eat(sess, kind, base_score, grow)

        # Powerup check
        collected = sess.powerups.check_collect(new_head)
        if collected:
            self._collect_powerup(sess, collected)

        # Challenge mode: add obstacle waves on level-up
        if sess.mode == "CHALLENGE" and sess.level > sess._challenge_level:
            sess.add_obstacle_wave()
            self._toast("CHALLENGE ESCALATES", "New obstacles spawned!")

    def _eat(self, sess: GameSession, kind: str, base_score: int, grow: int):
        mult         = sess.score_mult
        actual_score = int(base_score * mult)
        combo_mult   = sess.combo.eat()

        if kind == "poison":
            actual_score = int(FOOD_TYPES["poison"]["score"] * DIFFICULTY_CONFIG[sess.difficulty]["score_mult"])
            sess.score   = max(0, sess.score + actual_score)
            sess.combo.count = 0
            self.sound.play("eat_poison")
            self.shake.add(0.3)
            self.flash.trigger((150, 0, 220), 60, 12)
        else:
            sess.score  += actual_score
            sess.snake.grow(grow)
            self.sound.play("eat_bonus" if kind in ("bonus", "super") else "eat")
            if kind == "super":
                self.shake.add(0.15)
                self.flash.trigger((255, 80, 200), 40, 10)

        sess.stats["food_eaten"] += 1
        sess.stats["score"]       = sess.score
        sess.stats["max_length"]  = max(sess.stats["max_length"], len(sess.snake.body))

        # XP
        xp_gain = max(1, int(actual_score * 0.1))
        self.prog.add_xp(xp_gain)
        sess.stats["xp_earned"] = self.prog.xp

        # Floating score text
        hx, hy = sess.snake.head
        px = hx * CELL + CELL // 2
        py = hy * CELL + CELL // 2
        score_col = FOOD_TYPES[kind]["color"]
        sign = "+" if actual_score >= 0 else ""
        sess.particles.floating_text(px, py - 10, f"{sign}{actual_score}", score_col,
                                     self.fonts["sm"])
        if kind != "poison":
            sess.particles.explosion(px, py, FOOD_TYPES[kind]["color"],
                                     FOOD_TYPES[kind]["glow"],
                                     count=18 if kind in ("bonus","super") else 10)

        # Combo HUD
        if sess.combo.active:
            self._hud.set_combo(sess.combo.label)
            sess.stats["max_combo"] = max(sess.stats["max_combo"], sess.combo.count)
            if sess.combo.count in (5, 10):
                self.sound.play("combo")
                self.flash.trigger(clamp_col(lerp_color((80,255,160),(255,255,255),0.5)),
                                   80, 15)

        # Combo floating text for high combos
        if sess.combo.count >= 3:
            sess.particles.floating_text(px, py - 36, sess.combo.label,
                                         (255, 220, 50), self.fonts["sm"])

        # Level check
        leveled = sess.update_level()
        if leveled:
            self._level_up(sess)
            return

        # Achievement checks mid-game
        new_achs = self.prog.check_achievements(sess.stats)
        for ach in new_achs:
            self.sound.play("level_up")
            self._toast(f"🏆 {ach['title']}", ach["desc"])

    def _collect_powerup(self, sess: GameSession, kind: str):
        defn = POWERUP_TYPES[kind]
        sess.powerups.apply(kind)
        sess.stats["powerups_collected"] += 1

        # Apply instant effects
        if kind == "SHRINK":
            sess.snake.shrink(0.5)
            sess.particles.starburst(*sess.snake.pixel_head, defn.color, rays=12, size=40)
        else:
            sess.particles.powerup_burst(*sess.snake.pixel_head, defn.color)

        if kind == "SHIELD":
            self.sound.play("shield_on")
        else:
            self.sound.play("powerup")

        self.flash.trigger(defn.color, 50, 10)
        hx, hy = sess.snake.head
        sess.particles.floating_text(
            hx * CELL + CELL // 2, hy * CELL,
            defn.name, defn.color, self.fonts["sm"])

    def _level_up(self, sess: GameSession):
        self.sound.play("level_up")
        self.flash.trigger(sess.theme["accent"], 160, 25)
        self.shake.add(0.4)
        cx, cy = W // 2, H // 2
        sess.particles.level_up_burst(cx, cy, sess.theme["accent"])

        # Add obstacles in challenge mode
        if sess.mode == "CHALLENGE":
            sess.add_obstacle_wave()

        self._levelup = LevelUpOverlay(self.fonts, sess.level,
                                       sess.theme["name"], sess.theme["accent"])
        self.state = self.STATE_LEVELUP

        new_achs = self.prog.check_achievements(sess.stats)
        for ach in new_achs:
            self._toast(f"🏆 {ach['title']}", ach["desc"])

    def _die(self, sess: GameSession):
        if not sess.alive and self.state == self.STATE_DEAD:
            return
        sess.alive = False
        self.state = self.STATE_DEAD

        self.sound.play("death")
        self.shake.add(1.0)
        self.flash.trigger((255, 30, 50), 200, 30)

        # Death particles
        sess.particles.death_burst(sess.snake.pixel_segments)

        # Hi score
        new_hs = self.prog.update_hi_score(sess.difficulty, sess.score)
        if new_hs:
            self.flash.trigger((255, 220, 50), 100, 20)

        # XP from final score
        xp = max(10, sess.score // 10)
        self.prog.add_xp(xp)
        sess.stats["xp_earned"] += xp

        # Record game + achievements
        self.prog.record_game(sess.mode, sess.difficulty, sess.stats)
        new_achs = self.prog.check_achievements(sess.stats)
        for ach in new_achs:
            self._toast(f"🏆 {ach['title']}", ach["desc"])

        self.prog.save()

        self._game_over = GameOverScreen(self.fonts, {
            "score":     sess.score,
            "hi":        self.prog.hi_score(sess.difficulty),
            "length":    len(sess.snake.body),
            "level":     sess.level,
            "max_combo": sess.stats["max_combo"],
            "xp_earned": sess.stats["xp_earned"],
        }, new_hs)

    def _toast(self, title: str, desc: str):
        self._toasts.append(AchievementToast(self.fonts, title, desc))

    # ── Draw ─────────────────────────────────────────────────────────────────

    def _draw(self):
        surf = self.game_surf
        surf.fill(PAL["bg"])

        if self.state == self.STATE_MENU:
            self._menu.draw(surf)
            self._settings.draw(surf)
        else:
            self._draw_game(surf)

            if self.state == self.STATE_PAUSED:
                self._pause.draw(surf)
                self._settings.draw(surf)
            elif self.state == self.STATE_DEAD and self._game_over:
                self._game_over.draw(surf)
            elif self.state == self.STATE_LEVELUP and self._levelup:
                self._levelup.draw(surf)

        # Post-processing (scanlines always on)
        self.scanlines.draw(surf)

        # Achievement toasts (drawn on top)
        for i, toast in enumerate(reversed(self._toasts[-3:])):
            old_y = toast.y if hasattr(toast, 'y') else None
            toast.draw(surf)

        # Apply screen shake
        ox, oy = self.shake.offset
        self.screen.blit(surf, (ox, oy))
        pygame.display.flip()

    def _draw_game(self, surf: pygame.Surface):
        sess = self.session
        if not sess:
            return

        t     = self._tick
        theme = sess.theme
        ac    = theme["accent"]

        # ── Background ───────────────────────────────────────────────────────
        surf.fill(theme["bg"])

        # Animated grid
        grid_col = clamp_col(tuple(max(0, c - 220) for c in ac))
        grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        grid_alpha = 30
        for c in range(0, W, CELL):
            pygame.draw.line(grid_surf, (*grid_col, grid_alpha), (c, 0), (c, H))
        for r in range(0, H, CELL):
            pygame.draw.line(grid_surf, (*grid_col, grid_alpha), (0, r), (W, r))
        surf.blit(grid_surf, (0, 0))

        # Fog on high levels
        if theme["fog"] and sess.level >= 3:
            density = min(1.0, (sess.level - 2) * 0.2)
            self.fog.draw(surf, theme["bg"], density)

        # ── Obstacles ────────────────────────────────────────────────────────
        for obs in sess.challenge_obstacles:
            obs.draw(surf, t, ac)

        # ── Food ─────────────────────────────────────────────────────────────
        sess.food.draw(surf, t)

        # ── World power-ups ───────────────────────────────────────────────────
        sess.powerups.draw_world(surf, self.fonts)

        # ── Snake ────────────────────────────────────────────────────────────
        ghost  = sess.powerups.has("GHOST")
        shield = sess.powerups.has("SHIELD")
        sess.snake.draw(surf, t, ghost=ghost, shield=shield)

        # ── Particles ────────────────────────────────────────────────────────
        if self._settings.values.get("particles", True):
            sess.particles.draw(surf)

        # ── Screen effects ────────────────────────────────────────────────────
        self.flash.draw(surf)
        self.danger.draw(surf)
        self.vignette.draw(surf, theme["bg"], 0.6)

        # ── HUD ──────────────────────────────────────────────────────────────
        ghost_or_wrap = DIFFICULTY_CONFIG[sess.difficulty]["wrap"] or ghost
        hud_state = {
            "score":      sess.score,
            "hi_score":   self.prog.hi_score(sess.difficulty),
            "level":      sess.level,
            "mode":       sess.mode,
            "difficulty": sess.difficulty,
            "combo":      sess.combo.count,
            "length":     len(sess.snake.body),
            "xp":         self.prog.xp,
            "timer":      sess.timer,
            "fps":        self._fps_display,
        }
        self._hud.draw(surf, hud_state, t)

        # Active power-up bars
        sess.powerups.draw_hud(surf, self.fonts, 14, 58)

        # ── Combo timer bar ───────────────────────────────────────────────────
        if sess.combo.active:
            self._draw_combo_bar(surf, sess.combo, ac)

        # ── Ghost/wrap indicator ──────────────────────────────────────────────
        if ghost_or_wrap:
            s = self.fonts["tiny"].render("◎ WRAP", True, (80, 120, 255))
            surf.blit(s, (W - 80, 56))

        # ── Daily challenges sidebar ───────────────────────────────────────────
        self._draw_challenges_mini(surf, sess)

    def _draw_combo_bar(self, surf, combo, accent_col):
        """Horizontal combo timer bar at bottom of screen above XP."""
        frac = combo.bar_fraction
        if frac <= 0:
            return
        bw = 300
        bx = W // 2 - bw // 2
        by = H - 30

        # Track
        pygame.draw.rect(surf, (30, 35, 50), (bx, by, bw, 5), border_radius=2)
        # Fill — pulsing color
        col = clamp_col(lerp_color((255, 60, 60), accent_col, frac))
        fw  = int(bw * frac)
        if fw > 0:
            pygame.draw.rect(surf, col, (bx, by, fw, 5), border_radius=2)

        label = self.fonts["tiny"].render("COMBO TIMER", True, (100, 100, 120))
        surf.blit(label, (bx, by - 14))

    def _draw_challenges_mini(self, surf, sess):
        """Show daily challenges as tiny progress bars in corner."""
        challenges = self.prog.daily_challenges()
        x = W - 200
        y = 70
        header = self.fonts["tiny"].render("DAILY", True, (60, 70, 100))
        surf.blit(header, (x, y))
        y += 18
        for ch in challenges:
            frac = self.prog.daily_progress_frac(ch)
            done = frac >= 1.0
            col  = (50, 200, 80) if done else (60, 80, 120)
            bw   = 120
            pygame.draw.rect(surf, (20, 25, 40), (x, y, bw, 5), border_radius=2)
            fw = int(bw * frac)
            if fw > 0:
                pygame.draw.rect(surf, col, (x, y, fw, 5), border_radius=2)
            tick_mark = "✓ " if done else ""
            label = self.fonts["tiny"].render(
                f"{tick_mark}{ch['desc'][:22]}", True,
                (80, 180, 80) if done else (60, 70, 90))
            surf.blit(label, (x, y + 7))
            y += 32


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  NEON SERPENT ARCADE EDITION  ")
    print("=" * 50)
    print("  Controls:  WASD / Arrows  │  P = Pause")
    print("             TAB = Settings │  M = Music")
    print("             F11 = Fullscreen")
    print("=" * 50)
    game = NeonSerpentGame()
    game.run()


if __name__ == "__main__":
    main()