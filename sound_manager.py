"""
sound_manager.py  --  Procedural audio engine
Works WITH numpy (better quality) OR WITHOUT numpy (pure Python fallback).
No external audio files required.
"""

import math
import random
import array

try:
    import numpy as np
    _NP = True
except ImportError:
    np = None
    _NP = False

try:
    import pygame
    _PG = True
except ImportError:
    _PG = False

SAMPLE_RATE = 44100


# -- Pure-Python helpers ------------------------------------------------------

def _sine_py(freq, dur_ms, amp=0.5):
    n = int(SAMPLE_RATE * dur_ms / 1000)
    return [amp * math.sin(2 * math.pi * freq * i / SAMPLE_RATE) for i in range(n)]

def _sweep_py(f0, f1, dur_ms, amp=0.5):
    n = int(SAMPLE_RATE * dur_ms / 1000)
    phase = 0.0
    out = []
    for i in range(n):
        t = i / max(n-1, 1)
        freq = f0 + (f1 - f0) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(amp * math.sin(phase))
    return out

def _noise_py(dur_ms, amp=0.3):
    n = int(SAMPLE_RATE * dur_ms / 1000)
    return [amp * (random.random() * 2 - 1) for _ in range(n)]

def _env_py(s, atk_ms=5, rel_ms=60):
    n = len(s)
    atk = min(int(SAMPLE_RATE * atk_ms / 1000), n)
    rel = min(int(SAMPLE_RATE * rel_ms / 1000), n)
    out = list(s)
    for i in range(atk):
        out[i] *= i / max(atk, 1)
    for i in range(rel):
        out[n - rel + i] *= (rel - i) / max(rel, 1)
    return out

def _mix_py(*lists):
    max_len = max((len(l) for l in lists), default=0)
    out = [0.0] * max_len
    for lst in lists:
        for i, v in enumerate(lst):
            out[i] += v
    return out

def _to_sound_py(samples):
    buf = array.array('h')
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 28000)
        buf.append(v)
        buf.append(v)
    return pygame.mixer.Sound(buffer=buf.tobytes())


# -- NumPy helpers ------------------------------------------------------------

def _sine_np(freq, dur_ms, amp=0.5):
    n = int(SAMPLE_RATE * dur_ms / 1000)
    t = np.linspace(0, dur_ms / 1000, n, endpoint=False)
    return (amp * np.sin(2 * math.pi * freq * t)).astype(np.float32)

def _sweep_np(f0, f1, dur_ms, amp=0.5, wave="sine"):
    n = int(SAMPLE_RATE * dur_ms / 1000)
    freqs = np.linspace(f0, f1, n)
    phase = np.cumsum(2 * math.pi * freqs / SAMPLE_RATE)
    if wave == "saw":
        a = amp * (2 * (phase / (2 * math.pi) % 1) - 1)
    elif wave == "square":
        a = amp * np.sign(np.sin(phase))
    else:
        a = amp * np.sin(phase)
    return a.astype(np.float32)

def _env_np(arr, atk_ms=5, dec_ms=20, sus=0.7, rel_ms=50):
    n = len(arr)
    env = np.ones(n, dtype=np.float32)
    atk = min(int(SAMPLE_RATE * atk_ms / 1000), n)
    dec = min(int(SAMPLE_RATE * dec_ms / 1000), n - atk)
    rel = min(int(SAMPLE_RATE * rel_ms / 1000), n - atk - dec)
    s_end = n - rel
    if atk > 0:       env[:atk] = np.linspace(0, 1, atk)
    if dec > 0:       env[atk:atk+dec] = np.linspace(1, sus, dec)
    if atk+dec < s_end: env[atk+dec:s_end] = sus
    if rel > 0:       env[s_end:] = np.linspace(sus, 0, n - s_end)
    return (arr * env).astype(np.float32)

def _mix_np(*arrs):
    ml = max(len(a) for a in arrs)
    out = np.zeros(ml, dtype=np.float32)
    for a in arrs:
        out[:len(a)] += a
    return out

def _to_sound_np(arr):
    arr = np.clip(arr, -1.0, 1.0)
    s16 = (arr * 28000).astype(np.int16)
    stereo = np.column_stack([s16, s16])
    return pygame.sndarray.make_sound(stereo)


# -- Sound generators ---------------------------------------------------------

def _gen(name):
    try:
        if _NP:
            return _gen_np(name)
        return _gen_py(name)
    except Exception as e:
        print(f"[Audio] gen '{name}': {e}")
        return None


def _gen_np(name):
    if name == "eat":
        a = _env_np(_sweep_np(300, 650, 80, 0.55), atk_ms=2, rel_ms=40)
        b = _env_np(_sine_np(900, 40, 0.2), rel_ms=30)
        return _to_sound_np(_mix_np(a, b))

    if name == "eat_bonus":
        layers = []
        for i, f in enumerate([523, 659, 784, 1047]):
            delay = int(SAMPLE_RATE * i * 0.04)
            tone = _env_np(_sine_np(f, 180, 0.35), rel_ms=80)
            pad = np.zeros(delay + len(tone), dtype=np.float32)
            pad[delay:] = tone
            layers.append(pad)
        return _to_sound_np(_mix_np(*layers) * 0.55)

    if name == "eat_poison":
        a = _env_np(_sweep_np(400, 80, 300, 0.45, "saw"), rel_ms=120)
        n = (0.1 * np.random.rand(len(a))).astype(np.float32)
        return _to_sound_np(_mix_np(a, n))

    if name == "death":
        layers = []
        for i, f in enumerate([220, 185, 155, 130]):
            delay = int(SAMPLE_RATE * i * 0.07)
            tone = _env_np(_sweep_np(f, f*0.5, 400, 0.45, "saw"), rel_ms=200)
            pad = np.zeros(delay + len(tone), dtype=np.float32)
            pad[delay:] = tone
            layers.append(pad)
        return _to_sound_np(_mix_np(*layers) * 0.6)

    if name == "level_up":
        notes = [523, 659, 784, 1047, 1319]
        layers = []
        for i, f in enumerate(notes):
            delay = int(SAMPLE_RATE * i * 0.07)
            tone = _env_np(_sine_np(f, 250, 0.4), rel_ms=150)
            pad = np.zeros(delay + len(tone), dtype=np.float32)
            pad[delay:] = tone
            layers.append(pad)
        return _to_sound_np(_mix_np(*layers) * 0.5)

    if name == "powerup":
        return _to_sound_np(_env_np(_sweep_np(400, 1200, 150, 0.45), rel_ms=80))

    if name == "powerup_expire":
        return _to_sound_np(_env_np(_sweep_np(600, 200, 200, 0.35, "square"), rel_ms=100))

    if name == "menu_select":
        a = _env_np(_sine_np(440, 60, 0.35), rel_ms=40)
        return _to_sound_np(a)

    if name == "menu_confirm":
        a = _env_np(_mix_np(_sine_np(523,80,0.35), _sine_np(784,80,0.25), _sine_np(1047,60,0.2)), rel_ms=60)
        return _to_sound_np(a)

    if name == "shield_on":
        return _to_sound_np(_env_np(_sweep_np(200, 800, 200, 0.4), rel_ms=80))

    if name == "shield_break":
        a = _sweep_np(800, 100, 300, 0.5, "square")
        n = (0.25 * np.random.rand(len(a))).astype(np.float32)
        return _to_sound_np(_env_np(_mix_np(a, n), rel_ms=100))

    if name == "combo":
        freq = 660 + random.randint(0, 440)
        return _to_sound_np(_env_np(_sine_np(freq, 100, 0.35), rel_ms=60))

    if name in ("beep_lo", "beep_hi"):
        freq = 880 if name == "beep_hi" else 660
        return _to_sound_np(_env_np(_sine_np(freq, 120, 0.45), atk_ms=3, rel_ms=60))

    return None


def _gen_py(name):
    if name == "eat":
        return _to_sound_py(_env_py(_sweep_py(300, 650, 80, 0.5), rel_ms=40))

    if name == "eat_bonus":
        a = _env_py(_mix_py(_sine_py(523,150,0.3), _sine_py(659,150,0.25), _sine_py(784,150,0.2)), rel_ms=80)
        return _to_sound_py(a)

    if name == "eat_poison":
        return _to_sound_py(_env_py(_sweep_py(400, 80, 250, 0.4), rel_ms=100))

    if name == "death":
        a = _env_py(_mix_py(_sweep_py(220, 80, 500, 0.35), _noise_py(500, 0.08)), rel_ms=200)
        return _to_sound_py(a)

    if name == "level_up":
        a = _env_py(_mix_py(_sine_py(523,200,0.3), _sine_py(659,200,0.25), _sine_py(784,200,0.2)), rel_ms=100)
        return _to_sound_py(a)

    if name in ("powerup", "shield_on"):
        return _to_sound_py(_env_py(_sweep_py(400, 1000, 150, 0.35), rel_ms=60))

    if name in ("menu_select", "combo"):
        return _to_sound_py(_env_py(_sine_py(440, 60, 0.3), rel_ms=40))

    if name == "menu_confirm":
        a = _env_py(_mix_py(_sine_py(523,80,0.3), _sine_py(784,80,0.25)), rel_ms=50)
        return _to_sound_py(a)

    if name in ("shield_break", "powerup_expire"):
        return _to_sound_py(_env_py(_sweep_py(600, 150, 200, 0.35), rel_ms=80))

    if name in ("beep_lo", "beep_hi"):
        freq = 880 if name == "beep_hi" else 660
        return _to_sound_py(_env_py(_sine_py(freq, 100, 0.4), rel_ms=50))

    return None


def _gen_bgm():
    """Generate looping background music."""
    if _NP:
        bpm = 110
        beat = 60.0 / bpm * 1000
        total_ms = beat * 4 * 8
        n = int(SAMPLE_RATE * total_ms / 1000)
        out = np.zeros(n, dtype=np.float32)
        # Bass
        bass = [55, 55, 65, 55, 73, 55, 65, 58]
        for i, note in enumerate(bass * 8):
            ts = int(i * beat / 2 * SAMPLE_RATE / 1000)
            tone = _env_np(_sweep_np(note, note*0.97, beat*0.45, 0.28, "saw"),
                           atk_ms=8, dec_ms=30, sus=0.5, rel_ms=40)
            end = min(ts + len(tone), n)
            out[ts:end] += tone[:end-ts]
        # Pads
        for f in [220, 277, 330, 415]:
            pad = _env_np(_sine_np(f, total_ms, 0.06), atk_ms=300, rel_ms=400)
            out[:len(pad)] += pad
        # Kick
        for b in range(32):
            if b % 4 in (0, 2):
                ts = int(b * beat * SAMPLE_RATE / 1000)
                kick = _env_np(_sweep_np(110, 35, beat*0.3, 0.4),
                               atk_ms=2, dec_ms=60, sus=0.05, rel_ms=60)
                end = min(ts + len(kick), n)
                out[ts:end] += kick[:end-ts]
        # Hi-hat
        for b in range(64):
            ts = int(b * beat / 2 * SAMPLE_RATE / 1000)
            hat_len = int(beat * 0.05 * SAMPLE_RATE / 1000)
            hat = _env_np((0.05 * np.random.rand(hat_len)).astype(np.float32), atk_ms=1, rel_ms=int(beat*0.03))
            end = min(ts + len(hat), n)
            out[ts:end] += hat[:end-ts]
        out = np.clip(out * 0.45, -1.0, 1.0)
        s16 = (out * 28000).astype(np.int16)
        stereo = np.column_stack([s16, s16])
        return pygame.sndarray.make_sound(stereo)
    else:
        # Simple pure-Python pad loop (~4 seconds)
        a = _env_py(_mix_py(
            _sine_py(110, 4000, 0.10),
            _sine_py(165, 4000, 0.08),
            _sine_py(220, 4000, 0.06),
        ), atk_ms=500, rel_ms=500)
        return _to_sound_py(a)


# -- SoundManager class -------------------------------------------------------

class SoundManager:
    NAMES = [
        "eat", "eat_bonus", "eat_poison", "death", "level_up",
        "powerup", "powerup_expire", "menu_select", "menu_confirm",
        "shield_on", "shield_break", "combo", "beep_lo", "beep_hi",
    ]

    def __init__(self):
        self.enabled   = False
        self.sfx_vol   = 0.7
        self.music_vol = 0.35
        self._sounds   = {}
        self._music_ch = None
        self._music_snd = None
        self._init()

    def _init(self):
        if not _PG:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 1024)
                pygame.mixer.init(SAMPLE_RATE, -16, 2, 1024)
            self.enabled = True
            status = "numpy ?" if _NP else "pure Python (no numpy)"
            print(f"[Audio] Mixer ready -- {status}")
            self._preload()
        except Exception as e:
            print(f"[Audio] Init failed ({e}) -- running silently")

    def _preload(self):
        ok = 0
        for name in self.NAMES:
            snd = _gen(name)
            if snd:
                self._sounds[name] = snd
                ok += 1
        print(f"[Audio] {ok}/{len(self.NAMES)} sounds loaded")

    def play(self, name, vol=None):
        if not self.enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.set_volume(vol if vol is not None else self.sfx_vol)
            snd.play()

    def start_music(self):
        if not self.enabled:
            return
        self.stop_music()
        try:
            self._music_snd = _gen_bgm()
            self._music_ch  = pygame.mixer.Channel(0)
            self._music_snd.set_volume(self.music_vol)
            self._music_ch.play(self._music_snd, loops=-1)
        except Exception as e:
            print(f"[Audio] Music: {e}")

    def stop_music(self):
        try:
            if self._music_ch:
                self._music_ch.stop()
        except Exception:
            pass

    def toggle_music(self):
        if self._music_ch and self._music_ch.get_busy():
            self.stop_music()
        else:
            self.start_music()

    def set_sfx_volume(self, v):
        self.sfx_vol = max(0.0, min(1.0, v))

    def set_music_volume(self, v):
        self.music_vol = max(0.0, min(1.0, v))
        if self._music_snd:
            try:
                self._music_snd.set_volume(self.music_vol)
            except Exception:
                pass