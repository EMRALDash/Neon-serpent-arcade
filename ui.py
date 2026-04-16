"""
ui.py  —  All UI: main menu, HUD, overlays, achievements toast, settings
"""

import pygame
import math
import random
from typing import Dict, Any, List, Tuple, Optional


W, H = 1120, 784
CELL = 28


def lerp(a, b, t): return a + (b - a) * t
def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))
def clamp_col(c):
    return tuple(max(0, min(255, int(v))) for v in c)


# ── Color Palette (Neon Noir) ────────────────────────────────────────────────
PAL = {
    "bg":       (4,   6,  14),
    "panel":    (8,  12,  24),
    "border":   (40, 80, 160),
    "accent1":  (80, 255, 160),   # neon green
    "accent2":  (180, 80, 255),   # neon purple
    "accent3":  (255, 200, 50),   # gold
    "danger":   (255, 60,  80),
    "text":     (220, 230, 255),
    "subtext":  (100, 120, 160),
    "white":    (255, 255, 255),
}


def draw_neon_rect(surf: pygame.Surface, color: Tuple,
                   rect: pygame.Rect, radius: int = 12,
                   glow_passes: int = 3, border_width: int = 2):
    """Draw a rectangle with a neon glow border."""
    for i in range(glow_passes, 0, -1):
        alpha = int(40 * i / glow_passes)
        r = rect.inflate(i * 3, i * 3)
        s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, r.width, r.height),
                         border_radius=radius + i)
        surf.blit(s, r.topleft)
    # Fill
    pygame.draw.rect(surf, PAL["panel"], rect, border_radius=radius)
    # Border
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=border_width)


def draw_text_shadow(surf, text, font, color, x, y, shadow_col=(0, 0, 0),
                     center=False, right=False, shadow_off=2):
    rendered = font.render(text, True, color)
    shadow   = font.render(text, True, shadow_col)
    if center:
        rx = x - rendered.get_width() // 2
    elif right:
        rx = x - rendered.get_width()
    else:
        rx = x
    surf.blit(shadow,   (rx + shadow_off, y + shadow_off))
    surf.blit(rendered, (rx, y))
    return rendered.get_width()


# ── Animated Background ──────────────────────────────────────────────────────

class AnimatedBackground:
    def __init__(self):
        self._nodes = [self._rand_node() for _ in range(60)]
        self._connections = []
        self._static_surf = self._build_static()
        self._grid_surf   = self._build_grid()
        self.tick = 0

    def _rand_node(self):
        return {
            "x": random.uniform(0, W),
            "y": random.uniform(0, H),
            "vx": random.uniform(-0.3, 0.3),
            "vy": random.uniform(-0.3, 0.3),
            "r": random.uniform(1.5, 4),
            "col": random.choice([PAL["accent1"], PAL["accent2"], PAL["border"]]),
            "alpha": random.randint(40, 120),
        }

    def _build_static(self):
        s = pygame.Surface((W, H))
        s.fill(PAL["bg"])
        # Stars
        for _ in range(300):
            x = random.randint(0, W)
            y = random.randint(0, H)
            v = random.randint(20, 80)
            s.set_at((x, y), (v // 4, v // 3, v))
        return s

    def _build_grid(self):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        gc = (*PAL["border"], 20)
        for c in range(0, W, CELL):
            pygame.draw.line(s, gc, (c, 0), (c, H))
        for r in range(0, H, CELL):
            pygame.draw.line(s, gc, (0, r), (W, r))
        return s

    def update(self):
        self.tick += 1
        for n in self._nodes:
            n["x"] += n["vx"]
            n["y"] += n["vy"]
            if n["x"] < 0 or n["x"] > W: n["vx"] *= -1
            if n["y"] < 0 or n["y"] > H: n["vy"] *= -1

    def draw(self, surf: pygame.Surface):
        surf.blit(self._static_surf, (0, 0))
        surf.blit(self._grid_surf,   (0, 0))

        # Connection lines between nearby nodes
        node_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for i, n1 in enumerate(self._nodes):
            for n2 in self._nodes[i+1:]:
                dx = n1["x"] - n2["x"]
                dy = n1["y"] - n2["y"]
                d  = math.hypot(dx, dy)
                if d < 140:
                    alpha = int(50 * (1 - d / 140))
                    col = lerp_color(n1["col"], n2["col"], 0.5)
                    pygame.draw.line(node_surf, (*col, alpha),
                                     (int(n1["x"]), int(n1["y"])),
                                     (int(n2["x"]), int(n2["y"])), 1)

        for n in self._nodes:
            alpha = n["alpha"]
            r = int(n["r"])
            pygame.draw.circle(node_surf, (*n["col"], alpha),
                               (int(n["x"]), int(n["y"])), r)
        surf.blit(node_surf, (0, 0))

    def draw_game_bg(self, surf: pygame.Surface, theme_col: Tuple):
        """Lighter version for in-game background."""
        surf.fill(PAL["bg"])
        surf.blit(self._grid_surf, (0, 0))


# ── HUD ─────────────────────────────────────────────────────────────────────

class HUD:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self._score_display  = 0
        self._score_target   = 0
        self._combo_alpha    = 0.0
        self._combo_text     = ""
        self._fps_samples    = []

    def update(self, score: int):
        self._score_target = score
        # Smooth score counter
        diff = self._score_target - self._score_display
        if diff != 0:
            self._score_display += max(1, diff // 4)
            if abs(self._score_target - self._score_display) < 2:
                self._score_display = self._score_target
        # Combo alpha decay
        if self._combo_alpha > 0:
            self._combo_alpha = max(0, self._combo_alpha - 0.025)

    def set_combo(self, text: str):
        self._combo_text  = text
        self._combo_alpha = 1.0

    def draw(self, surf: pygame.Surface, game_state: dict, tick: int):
        score    = self._score_display
        hi       = game_state.get("hi_score", 0)
        level    = game_state.get("level", 1)
        mode     = game_state.get("mode", "CLASSIC")
        diff     = game_state.get("difficulty", "MEDIUM")
        combo    = game_state.get("combo", 0)
        length   = game_state.get("length", 6)
        xp       = game_state.get("xp", 0)
        timer    = game_state.get("timer", None)
        fps      = game_state.get("fps", 60)

        # ── Top bar ─────────────────────────────────────────────────────────
        bar = pygame.Surface((W, 52), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 180))
        surf.blit(bar, (0, 0))
        pygame.draw.line(surf, PAL["accent1"], (0, 52), (W, 52), 1)

        # Score
        pulse = abs(math.sin(tick * 0.08))
        sc = clamp_col(lerp_color(PAL["accent1"], PAL["white"], pulse * 0.3))
        draw_text_shadow(surf, f"{score:,}", self.fonts["score"], sc, 18, 6)

        # Hi score
        draw_text_shadow(surf, f"BEST {hi:,}", self.fonts["sm"], PAL["subtext"], 18, 34)

        # Level + Mode (center)
        lc = clamp_col(lerp_color(PAL["accent2"], PAL["white"], pulse * 0.2))
        draw_text_shadow(surf, f"LEVEL {level}", self.fonts["med"], lc, W // 2, 8, center=True)
        draw_text_shadow(surf, mode, self.fonts["tiny"], PAL["subtext"], W // 2, 32, center=True)

        # Combo
        if combo >= 2:
            cc = lerp_color(PAL["accent1"], PAL["accent3"], min(1, combo / 10))
            draw_text_shadow(surf, f"× {combo} COMBO", self.fonts["med"],
                             clamp_col(cc), W // 2 + 140, 10, center=True)

        # Right side: diff + length
        from powerups import POWERUP_TYPES   # avoid circular; fine at runtime
        diff_colors = {"EASY": (80, 200, 80), "MEDIUM": (240, 180, 40), "HARD": (255, 60, 60)}
        dc = diff_colors.get(diff, PAL["text"])
        draw_text_shadow(surf, diff, self.fonts["med"], dc, W - 18, 6, right=True)
        draw_text_shadow(surf, f"LEN {length}", self.fonts["tiny"], PAL["subtext"], W - 18, 32, right=True)

        # ── Timer (Time Attack / Countdown) ─────────────────────────────────
        if timer is not None:
            self._draw_timer(surf, timer, tick)

        # ── Bottom XP bar ───────────────────────────────────────────────────
        self._draw_xp_bar(surf, xp, level)

        # ── Combo floating text ─────────────────────────────────────────────
        if self._combo_alpha > 0 and self._combo_text:
            alpha = int(255 * self._combo_alpha)
            cs = self.fonts["combo"].render(self._combo_text, True, PAL["accent3"])
            cs.set_alpha(alpha)
            surf.blit(cs, (W // 2 - cs.get_width() // 2, H // 2 - 60))

        # FPS (tiny corner)
        fps_s = self.fonts["tiny"].render(f"{int(fps)} FPS", True, (50, 60, 80))
        surf.blit(fps_s, (W - 52, H - 18))

    def _draw_timer(self, surf, timer, tick):
        secs  = int(timer)
        millis = int((timer % 1) * 100)
        urgent = timer < 10
        col = PAL["danger"] if urgent else PAL["accent3"]
        if urgent:
            col = clamp_col(lerp_color(PAL["danger"], PAL["white"],
                                       abs(math.sin(tick * 0.15)) * 0.5))
        draw_text_shadow(surf, f"{secs:02d}.{millis:02d}", self.fonts["timer"],
                         col, W // 2, 55, center=True)

    def _draw_xp_bar(self, surf, xp, level):
        xp_per_level = 200 + level * 50
        frac = min(1.0, (xp % xp_per_level) / xp_per_level)
        bw   = W - 28
        by   = H - 16

        # Track
        pygame.draw.rect(surf, (20, 25, 40), (14, by, bw, 8), border_radius=4)
        # Fill
        fw = int(bw * frac)
        if fw > 0:
            grad = pygame.Surface((fw, 8), pygame.SRCALPHA)
            for xi in range(fw):
                t = xi / fw
                c = lerp_color(PAL["accent2"], PAL["accent1"], t)
                pygame.draw.line(grad, (*c, 200), (xi, 0), (xi, 7))
            surf.blit(grad, (14, by))
            # Glow tip
            gs = pygame.Surface((14, 8), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*PAL["accent1"], 160), (0, 0, 14, 8), border_radius=4)
            surf.blit(gs, (14 + fw - 7, by))

        draw_text_shadow(surf, f"XP", self.fonts["tiny"], PAL["subtext"], 14, by - 14)
        draw_text_shadow(surf, f"LVL {level + 1}", self.fonts["tiny"], PAL["subtext"],
                         W - 14, by - 14, right=True)


# ── Main Menu ────────────────────────────────────────────────────────────────

class MainMenu:
    MODES = ["CLASSIC", "TIME ATTACK", "CHALLENGE", "SURVIVAL"]
    MODE_DESC = {
        "CLASSIC":     "Endless snake — grow as long as you can",
        "TIME ATTACK":  "Max score before the clock runs out",
        "CHALLENGE":   "Obstacles & escalating hell",
        "SURVIVAL":    "Speed ramps up — how long can you last?",
    }
    MODE_ICONS = {
        "CLASSIC": "∞", "TIME ATTACK": "⏱", "CHALLENGE": "⚔", "SURVIVAL": "💀",
    }

    def __init__(self, fonts: dict, hi_scores: dict, bg: "AnimatedBackground"):
        self.fonts     = fonts
        self.hi_scores = hi_scores
        self.bg        = bg
        self.tick      = 0
        self.mode_idx  = 0
        self.diff_idx  = 1
        self.diffs     = ["EASY", "MEDIUM", "HARD"]
        self.section   = "mode"   # "mode" | "diff"
        self._particles= []

    def handle_key(self, key) -> Optional[dict]:
        if key in (pygame.K_LEFT, pygame.K_a):
            if self.section == "mode":
                self.mode_idx = (self.mode_idx - 1) % len(self.MODES)
            else:
                self.diff_idx = (self.diff_idx - 1) % 3
            return None
        if key in (pygame.K_RIGHT, pygame.K_d):
            if self.section == "mode":
                self.mode_idx = (self.mode_idx + 1) % len(self.MODES)
            else:
                self.diff_idx = (self.diff_idx + 1) % 3
            return None
        if key in (pygame.K_UP, pygame.K_w):
            self.section = "mode"
        if key in (pygame.K_DOWN, pygame.K_s):
            self.section = "diff"
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            return {
                "mode":       self.MODES[self.mode_idx],
                "difficulty": self.diffs[self.diff_idx],
            }
        return None

    def draw(self, surf: pygame.Surface):
        self.tick += 1
        t = self.tick

        self.bg.update()
        self.bg.draw(surf)

        # Title
        title_y  = 50
        glow_amp = int(30 + 20 * math.sin(t * 0.04))
        gs = pygame.Surface((700, 100), pygame.SRCALPHA)
        pygame.draw.ellipse(gs, (*PAL["accent1"], glow_amp), (0, 0, 700, 100))
        surf.blit(gs, (W // 2 - 350, title_y - 20))

        title_col = clamp_col(lerp_color(PAL["accent1"], PAL["white"],
                                         (math.sin(t * 0.05) + 1) / 2 * 0.4))
        draw_text_shadow(surf, "NEON SERPENT", self.fonts["title"], title_col,
                         W // 2, title_y, center=True, shadow_off=4)

        sub_col = clamp_col(lerp_color(PAL["subtext"], PAL["text"],
                                        (math.sin(t * 0.07) + 1) / 2))
        draw_text_shadow(surf, "ARCADE  EDITION", self.fonts["subtitle"], sub_col,
                         W // 2, title_y + 82, center=True)

        # Decorative line
        pygame.draw.line(surf, PAL["accent1"], (W//2 - 280, 180), (W//2 + 280, 180), 1)

        # ── Mode selector ────────────────────────────────────────────────────
        section_active = self.section == "mode"
        header_col = PAL["accent1"] if section_active else PAL["subtext"]
        draw_text_shadow(surf, "▸ GAME MODE", self.fonts["med"], header_col, W // 2, 200, center=True)

        card_w, card_h = 220, 130
        total_w = len(self.MODES) * card_w + (len(self.MODES) - 1) * 20
        sx = W // 2 - total_w // 2

        for i, mode in enumerate(self.MODES):
            bx = sx + i * (card_w + 20)
            by = 228
            selected = (i == self.mode_idx) and section_active

            border_col = PAL["accent1"] if selected else PAL["border"]
            if selected:
                # Animated glow
                gp = (math.sin(t * 0.1) + 1) / 2
                border_col = clamp_col(lerp_color(PAL["accent1"], PAL["white"], gp * 0.3))

            draw_neon_rect(surf, border_col, pygame.Rect(bx, by, card_w, card_h),
                           radius=10, glow_passes=3 if selected else 1, border_width=2)

            icon = self.MODE_ICONS[mode]
            draw_text_shadow(surf, icon, self.fonts["icon"], border_col,
                             bx + card_w // 2, by + 10, center=True)
            draw_text_shadow(surf, mode, self.fonts["sm"],
                             PAL["white"] if selected else PAL["text"],
                             bx + card_w // 2, by + 66, center=True)
            desc = self.MODE_DESC[mode]
            # Wrap description
            words = desc.split()
            lines = []
            cur = ""
            for w in words:
                test = cur + " " + w if cur else w
                if self.fonts["tiny"].size(test)[0] < card_w - 12:
                    cur = test
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            for li, line in enumerate(lines[:2]):
                draw_text_shadow(surf, line, self.fonts["tiny"],
                                 PAL["subtext"] if not selected else PAL["text"],
                                 bx + card_w // 2, by + 90 + li * 16, center=True)

        # ── Difficulty selector ───────────────────────────────────────────────
        section_active = self.section == "diff"
        header_col = PAL["accent2"] if section_active else PAL["subtext"]
        draw_text_shadow(surf, "▸ DIFFICULTY", self.fonts["med"], header_col, W // 2, 385, center=True)

        diff_colors = [(80, 200, 80), (240, 180, 40), (255, 60, 60)]
        diff_mults  = ["×1", "×2", "×3"]
        diff_labels = ["EASY", "MEDIUM", "HARD"]
        dw, dh = 230, 80
        total_dw = 3 * dw + 2 * 20
        dsx = W // 2 - total_dw // 2

        for i, (dlabel, dcol, mult) in enumerate(zip(diff_labels, diff_colors, diff_mults)):
            bx = dsx + i * (dw + 20)
            by = 412
            selected = (i == self.diff_idx) and section_active
            border_col = dcol if selected else lerp_color(dcol, PAL["border"], 0.6)
            draw_neon_rect(surf, border_col, pygame.Rect(bx, by, dw, dh),
                           radius=10, glow_passes=3 if selected else 1)
            draw_text_shadow(surf, dlabel, self.fonts["sm"],
                             clamp_col(dcol) if selected else PAL["subtext"],
                             bx + dw // 2, by + 12, center=True)
            draw_text_shadow(surf, f"SCORE {mult}", self.fonts["tiny"],
                             PAL["text"] if selected else PAL["subtext"],
                             bx + dw // 2, by + 44, center=True)

        # ── Instructions ──────────────────────────────────────────────────────
        pygame.draw.line(surf, PAL["border"], (W//2 - 300, 515), (W//2 + 300, 515), 1)
        keys_a = int(120 + 120 * math.sin(t * 0.06))
        draw_text_shadow(surf, "← → to select   ↑↓ switch section   ENTER to play   ESC to quit",
                         self.fonts["tiny"], clamp_col((keys_a, keys_a, keys_a)),
                         W // 2, 525, center=True)

        # ── High scores ────────────────────────────────────────────────────────
        draw_text_shadow(surf, "— HIGH SCORES —", self.fonts["sm"], PAL["border"],
                         W // 2, 558, center=True)
        for i, (diff, dcol) in enumerate(zip(diff_labels, diff_colors)):
            hs = self.hi_scores.get(diff, 0)
            draw_text_shadow(surf, f"{diff}: {hs:,}", self.fonts["sm"],
                             clamp_col(dcol), W // 2 - 220 + i * 220, 580, center=True)

        # Achievements teaser
        draw_text_shadow(surf, "🏆 Achievements • Skins • XP • Daily Challenges",
                         self.fonts["tiny"], PAL["subtext"], W // 2, 625, center=True)

        # Version
        draw_text_shadow(surf, "v2.0  github-ready  •  Python + Pygame",
                         self.fonts["tiny"], (40, 50, 70), W - 14, H - 22, right=True)


# ── Game Over Screen ────────────────────────────────────────────────────────

class GameOverScreen:
    def __init__(self, fonts, stats: dict, new_hs: bool):
        self.fonts  = fonts
        self.stats  = stats
        self.new_hs = new_hs
        self.tick   = 0

    def draw(self, surf: pygame.Surface):
        self.tick += 1
        t = self.tick
        pulse = (math.sin(t * 0.08) + 1) / 2

        # Dark overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 + 40 * pulse)))
        surf.blit(overlay, (0, 0))

        # Panel
        pw, ph = 560, 420
        px, py = W // 2 - pw // 2, H // 2 - ph // 2
        draw_neon_rect(surf, PAL["danger"], pygame.Rect(px, py, pw, ph),
                       radius=16, glow_passes=4)

        # Title
        col = clamp_col(lerp_color(PAL["danger"], PAL["white"], pulse * 0.4))
        draw_text_shadow(surf, "GAME OVER", self.fonts["title_sm"], col,
                         W // 2, py + 24, center=True, shadow_off=3)

        if self.new_hs:
            nhc = clamp_col(lerp_color(PAL["accent3"], PAL["white"], pulse * 0.5))
            draw_text_shadow(surf, "✦ NEW HIGH SCORE ✦", self.fonts["med"], nhc,
                             W // 2, py + 90, center=True)

        # Stats
        stats_data = [
            ("SCORE",     f"{self.stats.get('score', 0):,}"),
            ("HIGH SCORE", f"{self.stats.get('hi', 0):,}"),
            ("LENGTH",    str(self.stats.get('length', 0))),
            ("LEVEL",     str(self.stats.get('level', 1))),
            ("COMBO MAX", f"×{self.stats.get('max_combo', 0)}"),
            ("XP EARNED", f"+{self.stats.get('xp_earned', 0)}"),
        ]
        for i, (label, val) in enumerate(stats_data):
            row_y  = py + 130 + i * 38
            draw_text_shadow(surf, label, self.fonts["sm"], PAL["subtext"], px + 40, row_y)
            draw_text_shadow(surf, val,   self.fonts["sm"], PAL["text"], px + pw - 40, row_y, right=True)
            if i < len(stats_data) - 1:
                pygame.draw.line(surf, PAL["border"],
                                 (px + 20, row_y + 30), (px + pw - 20, row_y + 30), 1)

        # Buttons
        buttons_y = py + ph - 70
        ba = int(180 + 75 * math.sin(t * 0.1))
        draw_text_shadow(surf, "ENTER  Retry    M  Menu    ESC  Quit",
                         self.fonts["sm"], clamp_col((ba, ba // 2, ba // 2)),
                         W // 2, buttons_y, center=True)


# ── Pause Overlay ────────────────────────────────────────────────────────────

class PauseOverlay:
    def __init__(self, fonts):
        self.fonts = fonts
        self.tick  = 0

    def draw(self, surf: pygame.Surface):
        self.tick += 1
        t = self.tick
        pulse = (math.sin(t * 0.06) + 1) / 2

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        pw, ph = 420, 220
        px, py = W // 2 - pw // 2, H // 2 - ph // 2
        draw_neon_rect(surf, PAL["accent3"], pygame.Rect(px, py, pw, ph),
                       radius=14, glow_passes=3)

        col = clamp_col(lerp_color(PAL["accent3"], PAL["white"], pulse * 0.3))
        draw_text_shadow(surf, "⏸  PAUSED", self.fonts["title_sm"], col,
                         W // 2, py + 30, center=True)

        draw_text_shadow(surf, "P  or  ENTER  to resume",
                         self.fonts["sm"], PAL["text"], W // 2, py + 110, center=True)
        draw_text_shadow(surf, "ESC  for menu",
                         self.fonts["sm"], PAL["subtext"], W // 2, py + 148, center=True)


# ── Level Up Overlay ────────────────────────────────────────────────────────

class LevelUpOverlay:
    def __init__(self, fonts, level: int, theme_name: str, theme_col: Tuple):
        self.fonts      = fonts
        self.level      = level
        self.theme_name = theme_name
        self.theme_col  = theme_col
        self.tick       = 0
        self.AUTO_ADVANCE = 220

    @property
    def done(self):
        return self.tick >= self.AUTO_ADVANCE

    def draw(self, surf: pygame.Surface):
        self.tick += 1
        t = self.tick
        tc = self.theme_col

        # Fade-in
        fade = min(1.0, t / 30)
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * fade)))
        surf.blit(overlay, (0, 0))

        if fade < 0.5:
            return

        pulse = (math.sin(t * 0.1) + 1) / 2
        glow_col = clamp_col(lerp_color(tc, (255,255,255), pulse * 0.3))

        # Big level text
        draw_text_shadow(surf, f"LEVEL  {self.level}", self.fonts["title"],
                         glow_col, W // 2, H // 2 - 80, center=True, shadow_off=5)

        draw_text_shadow(surf, self.theme_name, self.fonts["subtitle"],
                         clamp_col(tc), W // 2, H // 2 + 10, center=True)

        # Progress bar to auto-advance
        prog = t / self.AUTO_ADVANCE
        bw   = 300
        pygame.draw.rect(surf, (30, 35, 50),
                         (W // 2 - bw // 2, H // 2 + 70, bw, 6), border_radius=3)
        fw = int(bw * prog)
        if fw > 0:
            pygame.draw.rect(surf, clamp_col(tc),
                             (W // 2 - bw // 2, H // 2 + 70, fw, 6), border_radius=3)

        draw_text_shadow(surf, "ENTER to continue",
                         self.fonts["tiny"], PAL["subtext"], W // 2, H // 2 + 90, center=True)


# ── Achievement Toast ────────────────────────────────────────────────────────

class AchievementToast:
    def __init__(self, fonts, title: str, desc: str):
        self.fonts = fonts
        self.title = title
        self.desc  = desc
        self.life  = 1.0
        self.TOTAL_FRAMES = 300
        self.frame = 0

    @property
    def done(self):
        return self.frame >= self.TOTAL_FRAMES

    def draw(self, surf: pygame.Surface):
        self.frame += 1
        # Slide in from right
        slide_in  = min(1.0, self.frame / 30)
        slide_out = max(0.0, 1 - (self.frame - 260) / 40) if self.frame > 260 else 1.0
        alpha     = slide_in * slide_out

        tw, th = 320, 72
        tx = int(W - 20 - tw * alpha)
        ty = H - 100

        s = pygame.Surface((tw, th), pygame.SRCALPHA)
        a = int(200 * alpha)
        pygame.draw.rect(s, (8, 12, 24, a), (0, 0, tw, th), border_radius=10)
        pygame.draw.rect(s, (*PAL["accent3"], int(200 * alpha)), (0, 0, tw, th),
                         border_radius=10, width=2)

        icon_s = self.fonts["med"].render("🏆", True, PAL["accent3"])
        icon_s.set_alpha(int(255 * alpha))
        s.blit(icon_s, (10, 10))

        title_s = self.fonts["sm"].render(self.title, True, PAL["white"])
        title_s.set_alpha(int(255 * alpha))
        s.blit(title_s, (48, 8))

        desc_s = self.fonts["tiny"].render(self.desc, True, PAL["subtext"])
        desc_s.set_alpha(int(255 * alpha))
        s.blit(desc_s, (48, 34))

        surf.blit(s, (tx, ty))


# ── Settings Panel ───────────────────────────────────────────────────────────

class SettingsPanel:
    SETTINGS = [
        {"key": "sfx_vol",   "label": "SFX Volume",    "type": "slider", "min": 0, "max": 1.0, "step": 0.1},
        {"key": "music_vol", "label": "Music Volume",  "type": "slider", "min": 0, "max": 1.0, "step": 0.1},
        {"key": "particles", "label": "Particles",     "type": "toggle"},
        {"key": "shake",     "label": "Screen Shake",  "type": "toggle"},
        {"key": "trail",     "label": "Snake Trail",   "type": "toggle"},
    ]

    def __init__(self, fonts, current: dict):
        self.fonts   = fonts
        self.values  = dict(current)
        self.sel_idx = 0
        self.open    = False

    def toggle(self):
        self.open = not self.open

    def handle_key(self, key):
        if not self.open:
            return
        items = self.SETTINGS
        if key in (pygame.K_UP, pygame.K_w):
            self.sel_idx = (self.sel_idx - 1) % len(items)
        if key in (pygame.K_DOWN, pygame.K_s):
            self.sel_idx = (self.sel_idx + 1) % len(items)
        item = items[self.sel_idx]
        if item["type"] == "slider":
            if key in (pygame.K_LEFT, pygame.K_a):
                self.values[item["key"]] = max(item["min"], self.values.get(item["key"], 0.5) - item["step"])
            if key in (pygame.K_RIGHT, pygame.K_d):
                self.values[item["key"]] = min(item["max"], self.values.get(item["key"], 0.5) + item["step"])
        elif item["type"] == "toggle":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN):
                self.values[item["key"]] = not self.values.get(item["key"], True)

    def draw(self, surf):
        if not self.open:
            return
        pw, ph = 380, len(self.SETTINGS) * 54 + 80
        px = W - pw - 20
        py = 60
        draw_neon_rect(surf, PAL["accent2"], pygame.Rect(px, py, pw, ph), radius=12)
        draw_text_shadow(surf, "SETTINGS", self.fonts["sm"], PAL["accent2"],
                         px + pw // 2, py + 14, center=True)

        for i, item in enumerate(self.SETTINGS):
            iy = py + 54 + i * 54
            selected = (i == self.sel_idx)
            lc = PAL["white"] if selected else PAL["text"]
            draw_text_shadow(surf, item["label"], self.fonts["sm"], lc, px + 20, iy)

            if item["type"] == "slider":
                val = self.values.get(item["key"], 0.5)
                bw = 140
                bx = px + pw - 20 - bw
                pygame.draw.rect(surf, (30, 35, 50), (bx, iy + 4, bw, 10), border_radius=5)
                fw = int(bw * val / item["max"])
                if fw > 0:
                    pygame.draw.rect(surf, PAL["accent2"], (bx, iy + 4, fw, 10), border_radius=5)
                pct = self.fonts["tiny"].render(f"{int(val * 100)}%", True, PAL["subtext"])
                surf.blit(pct, (bx + bw + 6, iy + 4))
            elif item["type"] == "toggle":
                val = self.values.get(item["key"], True)
                col = PAL["accent1"] if val else PAL["danger"]
                lbl = "ON" if val else "OFF"
                draw_text_shadow(surf, lbl, self.fonts["sm"], col, px + pw - 20, iy, right=True)