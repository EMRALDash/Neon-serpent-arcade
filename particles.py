"""
particles.py  —  High-performance particle system
Supports: sparkle, trail, explosion, glow-ring, floating-text, shockwave
"""

import pygame
import math
import random
from typing import List


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def clamp_col(c):
    return tuple(max(0, min(255, int(v))) for v in c)


# ── Individual particle types ────────────────────────────────────────────────

class SparkParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "color2", "size", "gravity")

    def __init__(self, x, y, color, color2=None, speed_range=(1, 5)):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(*speed_range)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.max_life = random.uniform(0.5, 1.0)
        self.color = color
        self.color2 = color2 or (255, 255, 255)
        self.size = random.uniform(2, 6)
        self.gravity = random.uniform(0.05, 0.15)

    def update(self) -> bool:
        self.vy += self.gravity
        self.vx *= 0.96
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.04 / self.max_life
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        t = 1 - self.life
        col = clamp_col(lerp_color(self.color, self.color2, t))
        r = max(1, int(self.size * self.life))
        alpha = int(255 * self.life)
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*col, alpha), (r + 1, r + 1), r)
        surf.blit(s, (int(self.x) - r - 1, int(self.y) - r - 1))


class TrailParticle:
    __slots__ = ("x", "y", "life", "color", "size")

    def __init__(self, x, y, color, size=4):
        self.x = float(x)
        self.y = float(y)
        self.life = 1.0
        self.color = color
        self.size = size

    def update(self) -> bool:
        self.life -= 0.08
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        alpha = int(180 * self.life)
        r = max(1, int(self.size * self.life))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))


class GlowRing:
    __slots__ = ("x", "y", "color", "radius", "max_radius", "life", "width")

    def __init__(self, x, y, color, max_radius=60):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = 0.0
        self.max_radius = max_radius
        self.life = 1.0
        self.width = 3

    def update(self) -> bool:
        self.radius += 3.5
        self.life -= 0.04
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        alpha = int(200 * self.life)
        r = int(self.radius)
        if r < 2:
            return
        s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r + 2, r + 2), r, self.width)
        surf.blit(s, (int(self.x) - r - 2, int(self.y) - r - 2))


class FloatingText:
    __slots__ = ("x", "y", "text", "color", "life", "font", "scale", "vy")

    def __init__(self, x, y, text, color, font):
        self.x = float(x)
        self.y = float(y)
        self.text = str(text)
        self.color = color
        self.life = 1.0
        self.font = font
        self.scale = 1.0
        self.vy = -1.8

    def update(self) -> bool:
        self.y += self.vy
        self.vy *= 0.97
        self.life -= 0.022
        self.scale = min(1.4, self.scale + 0.02) if self.life > 0.8 else self.scale
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        alpha = int(255 * self.life)
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        # slight shadow
        shadow = self.font.render(self.text, True, (0, 0, 0))
        shadow.set_alpha(alpha // 2)
        rx = int(self.x) - rendered.get_width() // 2
        ry = int(self.y) - rendered.get_height() // 2
        surf.blit(shadow, (rx + 2, ry + 2))
        surf.blit(rendered, (rx, ry))


class Shockwave:
    __slots__ = ("x", "y", "color", "radius", "life", "max_r")

    def __init__(self, x, y, color=(255, 255, 255), max_r=100):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = 5.0
        self.life = 1.0
        self.max_r = max_r

    def update(self) -> bool:
        self.radius += (self.max_r - self.radius) * 0.18
        self.life -= 0.06
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        alpha = int(160 * self.life)
        r = int(self.radius)
        if r < 2:
            return
        thick = max(1, int(4 * self.life))
        s = pygame.Surface((r * 2 + thick, r * 2 + thick), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r + thick // 2, r + thick // 2), r, thick)
        surf.blit(s, (int(self.x) - r - thick // 2, int(self.y) - r - thick // 2))


class StarBurst:
    """Multi-ray star burst for level-up / powerup."""
    __slots__ = ("x", "y", "color", "rays", "life", "size")

    def __init__(self, x, y, color, rays=12, size=40):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.rays = rays
        self.life = 1.0
        self.size = size

    def update(self) -> bool:
        self.life -= 0.05
        self.size += 2
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        alpha = int(200 * self.life)
        s = pygame.Surface((self.size * 2 + 4, self.size * 2 + 4), pygame.SRCALPHA)
        cx = cy = self.size + 2
        for i in range(self.rays):
            angle = math.tau * i / self.rays
            px = cx + math.cos(angle) * self.size
            py = cy + math.sin(angle) * self.size
            pygame.draw.line(s, (*self.color, alpha), (cx, cy), (int(px), int(py)), 2)
        surf.blit(s, (int(self.x) - self.size - 2, int(self.y) - self.size - 2))


# ── ParticleSystem ───────────────────────────────────────────────────────────

class ParticleSystem:
    def __init__(self):
        self._sparks:    List[SparkParticle] = []
        self._trails:    List[TrailParticle] = []
        self._rings:     List[GlowRing] = []
        self._texts:     List[FloatingText] = []
        self._shockwaves: List[Shockwave] = []
        self._starbursts: List[StarBurst] = []

    # ── Emitters ────────────────────────────────────────────────────────────

    def explosion(self, x, y, color, color2=None, count=24, speed=(1.5, 5)):
        for _ in range(count):
            self._sparks.append(SparkParticle(x, y, color, color2, speed))
        self._rings.append(GlowRing(x, y, color, max_radius=50))
        self._shockwaves.append(Shockwave(x, y, color, max_r=60))

    def trail(self, x, y, color, size=5):
        self._trails.append(TrailParticle(x, y, color, size))

    def glow_ring(self, x, y, color, max_r=80):
        self._rings.append(GlowRing(x, y, color, max_r))

    def floating_text(self, x, y, text, color, font):
        self._texts.append(FloatingText(x, y, text, color, font))

    def shockwave(self, x, y, color=(255, 255, 255), max_r=120):
        self._shockwaves.append(Shockwave(x, y, color, max_r))

    def starburst(self, x, y, color, rays=12, size=40):
        self._starbursts.append(StarBurst(x, y, color, rays, size))

    def death_burst(self, segments, base_color=(255, 30, 80)):
        for sx, sy in segments[::2]:
            cx = sx + 14
            cy = sy + 14
            for _ in range(12):
                self._sparks.append(SparkParticle(cx, cy, base_color, (255, 200, 50), (2, 7)))
            self._rings.append(GlowRing(cx, cy, base_color, 35))
        # Big shockwave at head
        if segments:
            hx, hy = segments[0]
            self._shockwaves.append(Shockwave(hx + 14, hy + 14, (255, 100, 50), 160))
            self.starburst(hx + 14, hy + 14, (255, 80, 30), rays=16, size=50)

    def level_up_burst(self, cx, cy, color):
        for _ in range(40):
            self._sparks.append(SparkParticle(cx, cy, color, (255, 255, 255), (2, 8)))
        for r in [40, 80, 120]:
            self._rings.append(GlowRing(cx, cy, color, r))
        self._shockwaves.append(Shockwave(cx, cy, color, 200))
        self.starburst(cx, cy, color, rays=20, size=70)

    def powerup_burst(self, x, y, color):
        for _ in range(20):
            self._sparks.append(SparkParticle(x, y, color, (255, 255, 255), (1, 4)))
        self._rings.append(GlowRing(x, y, color, 60))
        self.starburst(x, y, color, rays=8, size=30)

    # ── Update & Draw ────────────────────────────────────────────────────────

    def update(self):
        self._sparks    = [p for p in self._sparks    if p.update()]
        self._trails    = [p for p in self._trails    if p.update()]
        self._rings     = [p for p in self._rings     if p.update()]
        self._texts     = [p for p in self._texts     if p.update()]
        self._shockwaves = [p for p in self._shockwaves if p.update()]
        self._starbursts = [p for p in self._starbursts if p.update()]

    def draw(self, surf: pygame.Surface):
        # Draw in order: back → front
        for p in self._shockwaves: p.draw(surf)
        for p in self._starbursts: p.draw(surf)
        for p in self._rings:     p.draw(surf)
        for p in self._trails:    p.draw(surf)
        for p in self._sparks:    p.draw(surf)
        for p in self._texts:     p.draw(surf)

    def clear(self):
        self._sparks.clear()
        self._trails.clear()
        self._rings.clear()
        self._texts.clear()
        self._shockwaves.clear()
        self._starbursts.clear()

    @property
    def count(self) -> int:
        return (len(self._sparks) + len(self._trails) + len(self._rings) +
                len(self._texts) + len(self._shockwaves) + len(self._starbursts))