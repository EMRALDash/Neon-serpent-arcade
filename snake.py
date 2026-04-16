"""
snake.py  --  Snake entity with neon rendering, trail effects, skin system
"""

import pygame
import math
import random
from typing import List, Tuple, Optional


CELL = 28
COLS = 40
ROWS = 28

# -- Snake Skins --------------------------------------------------------------

SKINS = {
    "default": {
        "name":   "Neon Serpent",
        "head":   (80, 255, 160),
        "body":   (40, 180, 100),
        "tail":   (20, 80,  50),
        "glow":   (80, 255, 160),
        "eye":    (255, 255, 255),
        "pupil":  (0, 0, 0),
        "trail":  (40, 255, 120),
        "unlock": 0,
    },
    "inferno": {
        "name":   "Inferno",
        "head":   (255, 100, 30),
        "body":   (220, 50,  10),
        "tail":   (120, 20,  0),
        "glow":   (255, 120, 40),
        "eye":    (255, 220, 0),
        "pupil":  (100, 0,  0),
        "trail":  (255, 80, 20),
        "unlock": 500,
    },
    "void": {
        "name":   "Void",
        "head":   (180, 80, 255),
        "body":   (120, 40, 200),
        "tail":   (50,  10, 100),
        "glow":   (200, 100, 255),
        "eye":    (255, 80, 255),
        "pupil":  (20,  0,  40),
        "trail":  (160, 50, 255),
        "unlock": 1000,
    },
    "ice": {
        "name":   "Glacial",
        "head":   (150, 230, 255),
        "body":   (80,  170, 220),
        "tail":   (40,  90,  140),
        "glow":   (180, 240, 255),
        "eye":    (255, 255, 255),
        "pupil":  (0,   50,  100),
        "trail":  (120, 200, 255),
        "unlock": 2000,
    },
    "gold": {
        "name":   "Auric",
        "head":   (255, 220, 50),
        "body":   (200, 160, 20),
        "tail":   (120, 90,  0),
        "glow":   (255, 240, 100),
        "eye":    (255, 80,  0),
        "pupil":  (100, 30,  0),
        "trail":  (255, 200, 40),
        "unlock": 5000,
    },
}

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def clamp_col(c):
    return tuple(max(0, min(255, int(v))) for v in c)


class Snake:
    def __init__(self, skin_key: str = "default"):
        self.skin_key = skin_key
        self.skin     = SKINS[skin_key]
        self.reset()

    def reset(self):
        mid_x = COLS // 2
        mid_y = ROWS // 2
        self.body:     List[Tuple[int, int]] = [(mid_x - i, mid_y) for i in range(6)]
        self.dir:      Tuple[int, int] = (1, 0)
        self.next_dir: Tuple[int, int] = (1, 0)
        self.grow_pending: int = 0
        self.alive:    bool = True
        self._trail_positions: List[Tuple[float, float]] = []
        self._trail_max = 20

    def set_direction(self, new_dir: Tuple[int, int]):
        # Prevent 180-degree turn
        if new_dir[0] != -self.dir[0] or new_dir[1] != -self.dir[1]:
            self.next_dir = new_dir

    def move(self, wrap: bool = False) -> bool:
        """Move the snake. Returns True if alive, False on collision."""
        self.dir = self.next_dir
        hx, hy = self.body[0]
        nx = hx + self.dir[0]
        ny = hy + self.dir[1]

        if wrap:
            nx %= COLS
            ny %= ROWS
        else:
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                self.alive = False
                return False

        if (nx, ny) in self.body[2:]:
            self.alive = False
            return False

        self.body.insert(0, (nx, ny))
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

        # Record trail
        px = nx * CELL + CELL // 2
        py = ny * CELL + CELL // 2
        self._trail_positions.insert(0, (px, py))
        if len(self._trail_positions) > self._trail_max:
            self._trail_positions.pop()

        return True

    def grow(self, amount: int = 1):
        self.grow_pending += amount

    def shrink(self, fraction: float = 0.5):
        new_len = max(3, int(len(self.body) * fraction))
        self.body = self.body[:new_len]

    def set_skin(self, key: str):
        if key in SKINS:
            self.skin_key = key
            self.skin = SKINS[key]

    # -- Rendering ------------------------------------------------------------

    def draw(self, surf: pygame.Surface, tick: int,
             ghost: bool = False, shield: bool = False):
        skin = self.skin
        n = len(self.body)
        if n == 0:
            return

        # Ghost mode transparency
        base_alpha = 120 if ghost else 255

        for i, (bx, by) in enumerate(self.body):
            t_norm = i / max(n - 1, 1)
            col = lerp_color(skin["head"], skin["tail"], t_norm)

            # Pulse on head segment
            head_pulse = int(3 * abs(math.sin(tick * 0.12))) if i == 0 else 0
            padding = 2 - head_pulse if i == 0 else 3
            rx = bx * CELL + padding
            ry = by * CELL + padding
            rw = CELL - padding * 2
            rh = CELL - padding * 2
            radius = CELL // 3

            # -- Glow (head only) --------------------------------------------
            if i == 0:
                glow_size = CELL + 10 + head_pulse * 2
                gs = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                ga = int(60 * base_alpha / 255)
                gc = clamp_col(tuple(c + 20 for c in skin["glow"]))
                pygame.draw.rect(gs, (*gc, ga), (0, 0, glow_size, glow_size),
                                 border_radius=radius + 4)
                surf.blit(gs, (bx * CELL - (glow_size - CELL) // 2,
                               by * CELL - (glow_size - CELL) // 2))

            # -- Segment body ------------------------------------------------
            seg_surf = pygame.Surface((rw + 4, rh + 4), pygame.SRCALPHA)
            pygame.draw.rect(seg_surf, (*col, base_alpha),
                             (2, 2, rw, rh), border_radius=radius)
            # Highlight strip
            hl = clamp_col(tuple(min(255, c + 50) for c in col))
            pygame.draw.rect(seg_surf, (*hl, int(base_alpha * 0.6)),
                             (3, 3, rw // 2, rh // 3), border_radius=radius)
            surf.blit(seg_surf, (rx - 2, ry - 2))

            # Scale shine
            if i % 3 == 0 and i != 0:
                sc = clamp_col(tuple(min(255, c + 30) for c in col))
                scale_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(scale_surf, (*sc, 80), (3, 3), 3)
                surf.blit(scale_surf, (bx * CELL + CELL // 2 - 3,
                                       by * CELL + CELL // 2 - 3))

        # -- Eyes ------------------------------------------------------------
        self._draw_eyes(surf, tick, base_alpha, shield)

        # -- Tongue ----------------------------------------------------------
        if tick % 24 < 12 and not ghost:
            self._draw_tongue(surf, tick)

        # -- Shield ring -----------------------------------------------------
        if shield:
            self._draw_shield(surf, tick)

    def _draw_eyes(self, surf, tick, alpha, shield):
        skin = self.skin
        hx, hy = self.body[0]
        cx = hx * CELL + CELL // 2
        cy = hy * CELL + CELL // 2
        dx, dy = self.dir
        perp_x, perp_y = -dy, dx

        eye_offset = 5
        e1x = cx + dx * 5 + perp_x * eye_offset
        e1y = cy + dy * 5 + perp_y * eye_offset
        e2x = cx + dx * 5 - perp_x * eye_offset
        e2y = cy + dy * 5 - perp_y * eye_offset

        for ex, ey in [(e1x, e1y), (e2x, e2y)]:
            # White sclera
            pygame.draw.circle(surf, (*skin["eye"], alpha), (ex, ey), 4)
            # Pupil
            pygame.draw.circle(surf, (*skin["pupil"], alpha),
                               (ex + dx, ey + dy), 2)
            # Iris glow
            pygame.draw.circle(surf, (*skin["glow"], 100), (ex, ey), 5, 1)

    def _draw_tongue(self, surf, tick):
        hx, hy = self.body[0]
        cx = hx * CELL + CELL // 2
        cy = hy * CELL + CELL // 2
        dx, dy = self.dir
        tongue_len = 10 + int(4 * math.sin(tick * 0.4))
        fork_len   = 5
        tcol = (255, 50, 80)

        base  = (cx + dx * (CELL // 2 + 1), cy + dy * (CELL // 2 + 1))
        mid   = (base[0] + dx * tongue_len, base[1] + dy * tongue_len)
        perp  = (-dy, dx)
        fork1 = (mid[0] + dx * fork_len + perp[0] * fork_len,
                 mid[1] + dy * fork_len + perp[1] * fork_len)
        fork2 = (mid[0] + dx * fork_len - perp[0] * fork_len,
                 mid[1] + dy * fork_len - perp[1] * fork_len)

        pygame.draw.line(surf, tcol, base, mid, 2)
        pygame.draw.line(surf, tcol, mid, fork1, 2)
        pygame.draw.line(surf, tcol, mid, fork2, 2)

    def _draw_shield(self, surf, tick):
        hx, hy = self.body[0]
        cx = hx * CELL + CELL // 2
        cy = hy * CELL + CELL // 2
        r  = CELL + int(4 * math.sin(tick * 0.1))
        alpha = int(160 + 80 * math.sin(tick * 0.12))
        s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(s, (80, 180, 255, alpha), (r + 4, r + 4), r, 3)
        # Inner shimmer
        pygame.draw.circle(s, (200, 230, 255, alpha // 3), (r + 4, r + 4), r - 2)
        surf.blit(s, (cx - r - 4, cy - r - 4))

    def draw_trail(self, surf: pygame.Surface, particle_sys, tick: int):
        """Emit trail particles from the current head position."""
        if len(self.body) < 2:
            return
        col = self.skin["trail"]
        hx, hy = self.body[0]
        px = hx * CELL + CELL // 2
        py = hy * CELL + CELL // 2
        if tick % 2 == 0:
            particle_sys.trail(px, py, col, size=random.randint(3, 6))

    @property
    def head(self) -> Tuple[int, int]:
        return self.body[0]

    @property
    def pixel_head(self) -> Tuple[int, int]:
        hx, hy = self.body[0]
        return (hx * CELL + CELL // 2, hy * CELL + CELL // 2)

    @property
    def pixel_segments(self) -> List[Tuple[int, int]]:
        return [(bx * CELL, by * CELL) for bx, by in self.body]