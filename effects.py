"""
effects.py  —  Screen shake, slow motion, flash, vignette, scanlines
"""

import pygame
import math
import random


W, H = 1120, 784


class ScreenShake:
    def __init__(self):
        self.trauma  = 0.0
        self.ox      = 0
        self.oy      = 0
        self._DECAY  = 0.05

    def add(self, amount: float):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self):
        if self.trauma > 0:
            s = self.trauma ** 2
            self.ox = int(random.uniform(-20, 20) * s)
            self.oy = int(random.uniform(-20, 20) * s)
            self.trauma = max(0, self.trauma - self._DECAY)
        else:
            self.ox = self.oy = 0

    @property
    def offset(self):
        return (self.ox, self.oy)

    @property
    def active(self) -> bool:
        return self.trauma > 0.01


class SlowMotion:
    """Controls game tick speed for cinematic slow-down."""
    def __init__(self):
        self.factor  = 1.0    # 1.0 = normal, <1.0 = slow
        self.target  = 1.0
        self._timer  = 0

    def trigger(self, factor: float = 0.25, duration: int = 60):
        self.target  = factor
        self._timer  = duration

    def update(self):
        if self._timer > 0:
            self._timer -= 1
            self.factor = self.target
        else:
            # Ease back to 1.0
            self.factor = min(1.0, self.factor + 0.05)
            self.target = 1.0

    @property
    def active(self) -> bool:
        return self.factor < 0.99


class ScreenFlash:
    """Full-screen colour flash for impacts."""
    def __init__(self):
        self._flashes = []

    def trigger(self, color=(255,255,255), alpha_start=180, duration=20):
        self._flashes.append({
            "color": color,
            "alpha": alpha_start,
            "decay": alpha_start / duration,
        })

    def update(self):
        for f in self._flashes:
            f["alpha"] -= f["decay"]
        self._flashes = [f for f in self._flashes if f["alpha"] > 0]

    def draw(self, surf: pygame.Surface):
        for f in self._flashes:
            alpha = int(max(0, f["alpha"]))
            if alpha == 0:
                continue
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((*f["color"], alpha))
            surf.blit(s, (0, 0))


class Vignette:
    def __init__(self):
        self._cache = {}

    def draw(self, surf: pygame.Surface, color=(0,0,0), intensity=0.8):
        key = (color, round(intensity, 2))
        if key not in self._cache:
            self._cache[key] = self._build(color, intensity)
        surf.blit(self._cache[key], (0, 0))

    def _build(self, color, intensity):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, cy = W // 2, H // 2
        max_r  = math.hypot(cx, cy)
        for step in range(0, int(max_r), 6):
            t     = step / max_r
            alpha = int(255 * intensity * (1 - t) ** 2)
            if alpha <= 0:
                break
            r_w = W - int(step * W / max_r) * 2
            r_h = H - int(step * H / max_r) * 2
            if r_w <= 0 or r_h <= 0:
                break
            pygame.draw.rect(s, (*color, alpha),
                             (W // 2 - r_w // 2, H // 2 - r_h // 2, r_w, r_h),
                             width=6)
        return s


class ScanLines:
    def __init__(self, alpha=15):
        self._surf = self._build(alpha)

    def _build(self, alpha):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(s, (0, 0, 0, alpha), (0, y), (W, y))
        return s

    def draw(self, surf: pygame.Surface):
        surf.blit(self._surf, (0, 0))


class DangerPulse:
    """Red edge pulse when snake is very close to death."""
    def __init__(self):
        self.active = False
        self._tick  = 0

    def set_active(self, active: bool):
        self.active = active

    def update(self):
        if self.active:
            self._tick += 1

    def draw(self, surf: pygame.Surface):
        if not self.active:
            return
        pulse = (math.sin(self._tick * 0.15) + 1) / 2
        alpha = int(80 * pulse)
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(0, 30, 4):
            a = int(alpha * (1 - i / 30))
            pygame.draw.rect(s, (255, 0, 0, a), (i, i, W - i*2, H - i*2), width=4)
        surf.blit(s, (0, 0))


class FogLayer:
    """Animated fog overlay for horror levels."""
    def __init__(self):
        self._surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self._tick = 0

    def draw(self, surf: pygame.Surface, color=(0,0,0), density=0.3):
        self._tick += 1
        t = self._tick
        self._surf.fill((0, 0, 0, 0))
        alpha_base = int(40 * density)
        for layer in range(3):
            for ix in range(0, W, 80):
                for iy in range(0, H, 80):
                    ox = math.sin(t * 0.004 * (layer+1) + ix * 0.01) * 40
                    oy = math.cos(t * 0.004 * (layer+1) + iy * 0.01) * 40
                    a  = int(alpha_base * (0.5 + 0.5 * math.sin(t * 0.01 + ix * 0.02)))
                    chunk = pygame.Surface((80, 80), pygame.SRCALPHA)
                    chunk.fill((*color, a))
                    self._surf.blit(chunk, (ix + ox, iy + oy))
        surf.blit(self._surf, (0, 0))