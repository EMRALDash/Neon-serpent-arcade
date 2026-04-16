"""
powerups.py  —  Power-up system
Types: SPEED, SLOW, DOUBLE_SCORE, SHIELD, MAGNET, GHOST, SHRINK
"""

import pygame
import math
import random
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


CELL = 28   # must match game.py


@dataclass
class PowerUpDef:
    name:     str
    symbol:   str
    color:    Tuple[int, int, int]
    duration: int    # frames (60fps)
    weight:   int    # spawn probability weight
    desc:     str


POWERUP_TYPES = {
    "SPEED":    PowerUpDef("SPEED BOOST",    "⚡", (255, 220, 50),  300, 15, "Move faster!"),
    "SLOW":     PowerUpDef("SLOW MOTION",    "❄", (80, 200, 255),  360, 15, "Time slows down"),
    "DOUBLE":   PowerUpDef("DOUBLE SCORE",   "✦", (255, 80, 200),  480, 20, "2× points!"),
    "SHIELD":   PowerUpDef("SHIELD",         "🛡", (50, 180, 255),  300, 12, "One free hit"),
    "MAGNET":   PowerUpDef("MAGNET",         "◎", (255, 150, 50),  360, 12, "Food attracts"),
    "GHOST":    PowerUpDef("GHOST MODE",     "👻", (180, 180, 255), 300, 8,  "Pass through walls"),
    "SHRINK":   PowerUpDef("SHRINK",         "◈", (100, 255, 160), 1,   8,  "Half the snake!"),
}

WEIGHTS = [d.weight for d in POWERUP_TYPES.values()]
KEYS    = list(POWERUP_TYPES.keys())


class WorldPowerUp:
    """A power-up sitting on the game grid waiting to be collected."""

    def __init__(self, grid_x: int, grid_y: int, kind: str):
        self.gx     = grid_x
        self.gy     = grid_y
        self.kind   = kind
        self.defn   = POWERUP_TYPES[kind]
        self.tick   = 0
        self.lifespan = 600   # disappears after 10s

    @property
    def pos(self):
        return (self.gx, self.gy)

    def update(self) -> bool:
        self.tick += 1
        return self.tick < self.lifespan

    def draw(self, surf: pygame.Surface, fonts):
        self.tick += 0   # draw tick handled in update
        cx = self.gx * CELL + CELL // 2
        cy = self.gy * CELL + CELL // 2
        t  = self.tick
        defn = self.defn
        col  = defn.color

        # Fade out in last 120 frames
        fade = 1.0
        if self.tick > self.lifespan - 120:
            fade = (self.lifespan - self.tick) / 120

        # Pulse + bob
        pulse = (math.sin(t * 0.1) + 1) / 2
        bob   = int(4 * math.sin(t * 0.07))
        draw_y = cy + bob

        # Outer glow ring
        glow_r = int(16 + 4 * pulse)
        gs = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
        ga = int(60 * fade * (0.5 + 0.5 * pulse))
        pygame.draw.circle(gs, (*col, ga), (glow_r + 4, glow_r + 4), glow_r + 4)
        surf.blit(gs, (cx - glow_r - 4, draw_y - glow_r - 4))

        # Core circle
        cr = int(12 + 3 * pulse)
        cs = pygame.Surface((cr * 2 + 2, cr * 2 + 2), pygame.SRCALPHA)
        ba = int(220 * fade)
        dark_col = tuple(max(0, c - 60) for c in col)
        pygame.draw.circle(cs, (*dark_col, ba), (cr + 1, cr + 1), cr)
        pygame.draw.circle(cs, (*col, ba), (cr + 1, cr + 1), cr, 3)
        surf.blit(cs, (cx - cr - 1, draw_y - cr - 1))

        # Symbol text
        sym_surf = fonts["powerup"].render(defn.symbol, True, col)
        sym_surf.set_alpha(int(220 * fade))
        surf.blit(sym_surf, (cx - sym_surf.get_width() // 2, draw_y - sym_surf.get_height() // 2))

        # Name label underneath
        label = fonts["tiny"].render(defn.name, True, col)
        label.set_alpha(int(180 * fade))
        surf.blit(label, (cx - label.get_width() // 2, draw_y + cr + 4))

    def pixel_pos(self):
        return (self.gx * CELL + CELL // 2, self.gy * CELL + CELL // 2)


class ActiveEffect:
    """One active power-up currently applied to the player."""

    def __init__(self, kind: str, duration: int):
        self.kind      = kind
        self.defn      = POWERUP_TYPES[kind]
        self.remaining = duration
        self.total     = duration

    @property
    def fraction(self) -> float:
        return self.remaining / self.total

    def tick(self) -> bool:
        self.remaining -= 1
        return self.remaining > 0


class PowerUpManager:
    """Manages world power-ups and active effects."""

    def __init__(self):
        self.world:   List[WorldPowerUp] = []
        self.active:  List[ActiveEffect] = []
        self._spawn_cd = 0
        self.SPAWN_INTERVAL = 420   # 7 seconds

    def reset(self):
        self.world.clear()
        self.active.clear()
        self._spawn_cd = 0

    def update(self, snake_body, food_pos):
        # Tick spawn cooldown
        self._spawn_cd += 1

        # Update active effects
        self.active = [e for e in self.active if e.tick()]

        # Update world power-ups (and auto-remove expired)
        self.world = [p for p in self.world if p.update()]

        return self._spawn_cd >= self.SPAWN_INTERVAL

    def try_spawn(self, snake_body, food_pos, cols, rows):
        if self._spawn_cd < self.SPAWN_INTERVAL:
            return
        # food_pos may be a list of positions — normalise to a set of tuples
        if isinstance(food_pos, (list, tuple)) and food_pos and isinstance(food_pos[0], (list, tuple)):
            food_set = {tuple(p) for p in food_pos}
        elif isinstance(food_pos, (list, tuple)) and len(food_pos) == 2 and isinstance(food_pos[0], int):
            food_set = {tuple(food_pos)}
        else:
            food_set = set()
        occupied = {tuple(p) for p in snake_body} | food_set | {p.pos for p in self.world}
        attempts = 0
        while attempts < 50:
            gx = random.randint(2, cols - 3)
            gy = random.randint(2, rows - 3)
            if (gx, gy) not in occupied:
                kind = random.choices(KEYS, WEIGHTS)[0]
                self.world.append(WorldPowerUp(gx, gy, kind))
                self._spawn_cd = 0
                return kind
            attempts += 1
        self._spawn_cd = 0

    def check_collect(self, head_pos) -> Optional[str]:
        for pw in self.world:
            if pw.pos == head_pos:
                self.world.remove(pw)
                return pw.kind
        return None

    def apply(self, kind: str):
        # Remove existing same type
        self.active = [e for e in self.active if e.kind != kind]
        defn = POWERUP_TYPES[kind]
        self.active.append(ActiveEffect(kind, defn.duration))

    def has(self, kind: str) -> bool:
        return any(e.kind == kind for e in self.active)

    def get_effect(self, kind: str) -> Optional[ActiveEffect]:
        for e in self.active:
            if e.kind == kind:
                return e
        return None

    def draw_world(self, surf: pygame.Surface, fonts):
        for pw in self.world:
            pw.draw(surf, fonts)

    def draw_hud(self, surf: pygame.Surface, fonts, x_start: int, y: int):
        """Draw active power-up icons with timer bars."""
        x = x_start
        bar_w = 90
        bar_h = 8
        icon_size = 24
        padding = 10

        for eff in self.active:
            defn = eff.defn
            col  = defn.color
            frac = eff.fraction

            # Background capsule
            total_w = bar_w + icon_size + padding
            bg = pygame.Surface((total_w + 8, 48), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 140), (0, 0, total_w + 8, 48), border_radius=8)
            pygame.draw.rect(bg, (*col, 80), (0, 0, total_w + 8, 48), border_radius=8, width=1)
            surf.blit(bg, (x - 4, y - 4))

            # Icon
            icon = fonts["powerup"].render(defn.symbol, True, col)
            surf.blit(icon, (x, y + 6))
            x += icon_size + 6

            # Name
            name_s = fonts["tiny"].render(defn.name, True, (200, 200, 200))
            surf.blit(name_s, (x, y + 2))

            # Timer bar track
            pygame.draw.rect(surf, (40, 40, 40), (x, y + 20, bar_w, bar_h), border_radius=4)
            # Filled
            fw = max(0, int(bar_w * frac))
            # Color shifts red when low
            bar_col = col if frac > 0.3 else lerp_color(col, (255, 60, 60), (0.3 - frac) / 0.3)
            if fw > 0:
                pygame.draw.rect(surf, bar_col, (x, y + 20, fw, bar_h), border_radius=4)

            # Seconds remaining
            secs = max(0, eff.remaining // 60)
            sec_s = fonts["tiny"].render(f"{secs}s", True, (180, 180, 180))
            surf.blit(sec_s, (x + bar_w + 4, y + 16))

            x += bar_w + icon_size + padding + 20


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))