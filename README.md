# Neon-serpent-arcade
Neon Serpent Arcade is a modern reimagining of the classic Snake game built with Python and Pygame. Designed as a polished indie-style arcade experience, it features multiple food types, power-ups, particle effects, neon visuals, combo scoring, and dynamic gameplay systems. 
# ◈ NEON SERPENT: Arcade Edition

> *A feature-complete, professionally engineered Snake game built as a modern indie arcade experience.*

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green)
![NumPy](https://img.shields.io/badge/NumPy-optional-orange)
![License](https://img.shields.io/badge/License-MIT-teal)
![Architecture](https://img.shields.io/badge/Architecture-Modular-purple)

---

## 🎮 What This Is

Neon Serpent is a complete ground-up redesign of a classic Snake game into a **polished indie arcade experience**. It was engineered to feel like a commercial release — not a weekend project.

Every system was designed from scratch:

| System | Description |
|--------|-------------|
| 🔊 **Procedural Audio** | All sounds synthesized via numpy — no audio files needed |
| ✨ **Particle Engine** | Sparks, trails, explosions, shockwaves, glow rings, floating text |
| ⚡ **Power-up System** | 7 unique powers with timed HUD indicators and visual effects |
| 🎯 **4 Game Modes** | Classic, Time Attack, Challenge, Survival |
| 🏆 **Progression** | XP, player levels, achievements, unlockable skins, daily challenges |
| 🌈 **7 Level Themes** | Dynamic atmosphere, fog, neon shifts, per-level visual identity |
| 🎨 **5 Snake Skins** | Unlockable via XP milestones |
| 🖥 **Cinematic FX** | Screen shake, flash, danger pulse, vignette, fog layers, scanlines |
| 🎵 **Procedural BGM** | Generative electronic loop with bass, pads, kick, hi-hats |
| 🔄 **Combo System** | Chain eating for multiplier bonuses up to ×5 |

---

## 🚀 Quick Start

### Requirements

```bash
pip install pygame numpy
```
> `numpy` enables procedural audio. Without it, the game runs silently.

### Run

```bash
python game.py
```

### Controls

| Key | Action |
|-----|--------|
| `W A S D` / `↑ ← ↓ →` | Move snake |
| `P` / `ESC` | Pause |
| `ENTER` | Confirm / Retry |
| `M` | Toggle music |
| `TAB` | Settings panel |
| `F11` | Toggle fullscreen |

---

## 🗂 Project Structure

```
neon-serpent/
│
├── game.py            ← Main orchestrator, game loop, all modes
├── snake.py           ← Snake entity, skins, animated rendering
├── food.py            ← Food types, magnet attraction, animations
├── powerups.py        ← 7 power-up types, world items, active effects
├── particles.py       ← Full particle system (sparks, rings, floats...)
├── effects.py         ← Screen shake, flash, vignette, fog, scanlines
├── sound_manager.py   ← Procedural audio synthesis engine
├── ui.py              ← All UI: menu, HUD, overlays, toasts, settings
├── progression.py     ← XP, achievements, daily challenges, combo
│
├── save_data.json     ← Auto-generated on first play
├── requirements.txt
└── README.md
```

---

## 🕹 Game Modes

### ∞ Classic
Endless snake. Focus on score, combo chains, and surviving longer. Levels unlock progressively as score increases.

### ⏱ Time Attack
90 seconds. Maximize your score before the clock dies. Countdown beeps at ≤10s. Panic mode.

### ⚔ Challenge
Fixed obstacles populate the grid. Every level-up adds a new obstacle wave. Mastery required.

### 💀 Survival
Speed increases every 10 seconds. No stopping, no mercy. Ghost wall-wrap available on EASY.

---

## ⚡ Power-Ups

| Icon | Name | Effect | Duration |
|------|------|--------|----------|
| ⚡ | Speed Boost | Moves faster | 5s |
| ❄ | Slow Motion | Time slows | 6s |
| ✦ | Double Score | ×2 all points | 8s |
| 🛡 | Shield | Survives one collision | 5s |
| ◎ | Magnet | Food drifts toward you | 6s |
| 👻 | Ghost Mode | Pass through walls | 5s |
| ◈ | Shrink | Cuts snake length in half | instant |

---

## 🎨 Level Themes

| # | Name | Atmosphere |
|---|------|------------|
| 1 | Cyber Grid | Classic neon green — clean and focused |
| 2 | Neon District | Purple shift, deeper shadows |
| 3 | Acid Rain | Vivid green with rolling fog |
| 4 | Blood Circuit | Red circuit horror with fog |
| 5 | Void Dimension | Deep blue void, minimal |
| 6 | Inferno Core | Orange flame energy |
| 7 | Singularity | Pure monochrome maximum intensity |

---

## 🏆 Achievements (19 total)

Examples: First Bite, Combo King, Unstoppable, Leviathan (length 100), Nightmare (level 7), Masochist (Hard mode), Close Call (shield save), Dedicated (3 daily challenges), Completionist (all modes)...

---

## 🐍 Unlockable Skins

| Skin | Unlock at XP |
|------|-------------|
| Neon Serpent (default) | 0 |
| Inferno | 500 XP |
| Void | 1,000 XP |
| Glacial | 2,000 XP |
| Auric | 5,000 XP |

---

## 🔧 Technical Architecture

### Design Principles
- **Single Responsibility** — each module owns exactly one concern
- **No global state** — `GameSession` encapsulates all per-game data
- **Procedural audio** — zero audio file dependencies via numpy synthesis
- **60 FPS stable** — particle system uses slots, effects use pre-rendered surfaces
- **Graceful degradation** — audio silently disabled if numpy unavailable

### Rendering Pipeline
```
theme_bg → grid → fog → obstacles → food → world_powerups →
snake → particles → post_fx (flash, danger, vignette, scanlines) →
HUD → powerup_bars → combo_bar → challenges_sidebar → toasts
```

### Performance Notes
- Particle slots avoid Python attribute dict overhead
- Vignette surface cached by (color, intensity) key
- Grid drawn once per frame as transparent surface blit
- Glow effects use pre-sized SRCALPHA surfaces; never resize per-frame

---

## 📦 GitHub Push

```bash
git init
git add .
git commit -m "✨ Neon Serpent Arcade Edition — full redesign"
git remote add origin https://github.com/YOUR_USERNAME/neon-serpent.git
git push -u origin main
```

---

## 🔮 Extending the Game

### Add a new game mode
1. Add the mode name to `MainMenu.MODES`
2. Handle it in `GameSession.__init__` (timer, obstacles, etc.)
3. Add mode-specific logic in `NeonSerpentGame._step`

### Add a new power-up
1. Add an entry to `POWERUP_TYPES` in `powerups.py`
2. Handle its effect in `NeonSerpentGame._step` and speed/mult properties

### Add a new skin
1. Add a dict to `SKINS` in `snake.py`
2. Set an `unlock` XP threshold
3. `ProgressionManager.check_skin_unlocks` handles the rest automatically

---

## 📜 License

MIT — free to fork, modify, publish, and distribute.

---

*Engineered with Python + Pygame. Sounds synthesized with NumPy. No assets required.*
