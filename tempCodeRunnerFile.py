"""
food.py  —  Food system with multiple types, animated rendering, magnet attraction
"""

import pygame
import math
import random
from typing import Tuple, List


CELL = 28
COLS = 40
ROWS = 28


FOOD_TYPES = {
    "normal":  {"score": 10, "color": (80,  255, 120), "glow": (40, 200, 80),  "weight": 60, "grow": 1},
    "bonus":   {"score": 30, "color": (255, 220, 0),   "glow": (200, 160, 0),  "weight": 20, "grow": 2},
    "super":   {"score": 60, "color": (255, 80,  200), "glow": (180, 30, 150), "weight": 10, "grow": 3},
    "poison":  {"score":-20, "color": (150, 0,   220), "glow": (80,  0,  140), "weight": 10, "grow": 1},
}

FOOD_KEYS    = list(FOOD_TYPES.keys())
FOOD_WEIGHTS = [FOOD_TYPES[k]["weight"] for k in FOOD_KEYS]


class Food:
    def __init__(self):
        self.gx:   int = 0
        self.gy:   int = 0
        self.kind: str = "normal"
        self.tick: int = 0
        # Pixel position (can drift toward snake for magnet)
        self._px: float = 0.0
        self._py: float = 0.0
        self._target_px: float = 0.0
        self._target_py: float = 0.0
        self.spawn([])

    def spawn(self, occupied: List[Tuple[int, int]]):
        occ_set = set(occupied)
        for _ in range(200):
            gx = random.randint(1, COLS - 2)
            gy = random.randint(2, ROWS - 2)
            if (gx, gy) not in occ_set:
                self.gx = gx
                self.gy = gy
                break
        self.kind = random.choices(FOOD_KEYS, FOOD_WEIGHTS)[0]
        self.tick = 0
        self._snap_pixel()

    def _snap_pixel(self):
        self._px = float(self.gx * CELL + CELL // 2)
        self._py = float(self.gy * CELL + CELL // 2)

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.gx, self.gy)

    @property
    def score(self) -> int:
        return FOOD_TYPES[self.kind]["score"]

    @property
    def grow_amount(self) -> int:
        return FOOD_TYPES[self.kind]["grow"]

    def update(self, magnet_target: Tuple[int, int] = None):
        self.tick += 1
        if magnet_target:
            tx, ty = magnet_target
            dx = tx - self._px
            dy = ty - self._py
            dist = math.hypot(dx, dy)
            if dist > 4:
                speed = min(6, 120 / max(dist, 1))
                self._px += dx / dist * speed
                self._py += dy / dist * speed

    def draw(self, surf: pygame.Surface, tick: int):
        defn  = FOOD_TYPES[self.kind]
        col   = defn["color"]
        gcol  = defn["glow"]
        t     = tick
        pulse = (math.sin(t * 0.1) + 1) / 2
        cx    = int(self._px)
        cy    = int(self._py)

        # Outer glow
        gr  = int(18 + 6 * pulse)
        gs  = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        ga  = int(50 + 30 * pulse)
        pygame.draw.circle(gs, (*gcol, ga), (gr, gr), gr)
        surf.blit(gs, (cx - gr, cy - gr))

        if self.kind == "normal":
            self._draw_normal(surf, cx, cy, col, pulse)
        elif self.kind == "bonus":
            self._draw_bonus(surf, cx, cy, col, pulse, t)
        elif self.kind == "super":
            self._draw_super(surf, cx, cy, col, pulse, t)
        elif self.kind == "poison":
            self._draw_poison(surf, cx, cy, col, pulse, t)

    def _draw_normal(self, surf, cx, cy, col, pulse):
        r = int(8 + 2 * pulse)
        pygame.draw.circle(surf, col, (cx, cy), r)
        # Shine
        hl = tuple(min(255, c + 80) for c in col)
        pygame.draw.circle(surf, hl, (cx - 2, cy - 2), r // 3)
        # Outline
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, 1)

    def _draw_bonus(self, surf, cx, cy, col, pulse, t):
        # Rotating star
        r = int(10 + 3 * pulse)
        angle_offset = t * 0.04
        pts = []
        for i in range(10):
            a = angle_offset + math.pi * i / 5 - math.pi / 2
            ri = r if i % 2 == 0 else r // 2
            pts.append((cx + int(ri * math.cos(a)), cy + int(ri * math.sin(a))))
        if len(pts) >= 3:
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, (255, 255, 200), pts, 2)
        # Center dot
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 3)

    def _draw_super(self, surf, cx, cy, col, pulse, t):
        # Diamond with orbiting sparkles
        r = int(11 + 3 * pulse)
        angle = t * 0.06
        diamond = [
            (cx,     cy - r),
            (cx + r, cy),
            (cx,     cy + r),
            (cx - r, cy),
        ]
        pygame.draw.polygon(surf, col, diamond)
        pygame.draw.polygon(surf, (255, 200, 255), diamond, 2)
        # Orbit
        for i in range(4):
            oa = angle + math.tau * i / 4
            ox = cx + int((r + 6) * math.cos(oa))
            oy = cy + int((r + 6) * math.sin(oa))
            pygame.draw.circle(surf, (255, 255, 255), (ox, oy), 2)

    def _draw_poison(self, surf, cx, cy, col, pulse, t):
        r = int(9 + 2 * pulse)
        # Circle with skull-X
        pygame.draw.circle(surf, col, (cx, cy), r)
        pygame.draw.circle(surf, (80, 0, 120), (cx, cy), r, 2)
        # X mark
        offset = r // 2
        pygame.draw.line(surf, (255, 255, 255), (cx - offset, cy - offset), (cx + offset, cy + offset), 2)
        pygame.draw.line(surf, (255, 255, 255), (cx + offset, cy - offset), (cx - offset, cy + offset), 2)
        # Drip
        drip_y = cy + r + int(3 * math.sin(t * 0.15))
        pygame.draw.circle(surf, col, (cx, drip_y), 3)


class MultiFood:
    """Manages a collection of food items on screen."""

    def __init__(self, max_food: int = 3):
        self.items: List[Food] = []
        self.max_food = max_food
        self._add_food([])

    def _add_food(self, occupied):
        f = Food()
        f.spawn(occupied)
        self.items.append(f)

    def update(self, snake_body, magnet_active: bool):
        target = None
        if magnet_active and snake_body:
            hx, hy = snake_body[0]
            target = (hx * CELL + CELL // 2, hy * CELL + CELL // 2)
        for f in self.items:
            f.update(magnet_target=target)

        # Ensure we have food
        occ = list(snake_body) + [f.pos for f in self.items]
        while len(self.items) < self.max_food:
            self._add_food(occ)

    def check_eat(self, head_pos: Tuple[int, int]) -> Tuple[bool, str, int, int]:
        """Returns (eaten, kind, score, grow)"""
        for f in self.items:
            if f.pos == head_pos:
                kind  = f.kind
                score = f.score
                grow  = f.grow_amount
                px, py = int(f._px), int(f._py)
                self.items.remove(f)
                return True, kind, score, grow
        return False, "", 0, 0

    def draw(self, surf: pygame.Surface, tick: int):
        for f in self.items:
            f.draw(surf, tick)

    @property
    def positions(self):
        return [f.pos for f in self.items]