"""
progression.py  —  XP, achievements, skins, daily challenges, leaderboard
"""

import json
import os
import time
import random
from datetime import date
from typing import List, Dict, Optional, Tuple


SAVE_FILE = "save_data.json"

# ── Achievement Definitions ──────────────────────────────────────────────────

ACHIEVEMENTS = {
    "first_eat":    {"title": "First Bite",      "desc": "Eat your first food",           "xp": 10,  "icon": "🍎"},
    "combo_5":      {"title": "Combo King",       "desc": "Reach a 5× combo",              "xp": 30,  "icon": "⚡"},
    "combo_10":     {"title": "Unstoppable",      "desc": "Reach a 10× combo",             "xp": 80,  "icon": "💥"},
    "length_20":    {"title": "Growing Pains",    "desc": "Reach length 20",               "xp": 25,  "icon": "📏"},
    "length_50":    {"title": "Serpent",           "desc": "Reach length 50",               "xp": 75,  "icon": "🐍"},
    "length_100":   {"title": "Leviathan",         "desc": "Reach length 100",              "xp": 200, "icon": "👑"},
    "score_100":    {"title": "Centurion",         "desc": "Score 100 points",              "xp": 20,  "icon": "💯"},
    "score_1000":   {"title": "Millennium",        "desc": "Score 1000 points",             "xp": 100, "icon": "🌟"},
    "score_5000":   {"title": "Transcendent",      "desc": "Score 5000 points",             "xp": 300, "icon": "🔮"},
    "level_3":      {"title": "Seasoned",          "desc": "Reach level 3",                 "xp": 40,  "icon": "📈"},
    "level_7":      {"title": "Nightmare",         "desc": "Reach maximum level",           "xp": 500, "icon": "☠"},
    "powerup_10":   {"title": "Power Hungry",      "desc": "Collect 10 power-ups",          "xp": 50,  "icon": "⚡"},
    "survive_60s":  {"title": "Survivor",          "desc": "Survive 60 seconds",            "xp": 35,  "icon": "⏱"},
    "survive_300s": {"title": "Endurance Master",  "desc": "Survive 5 minutes",             "xp": 200, "icon": "🏅"},
    "hard_mode":    {"title": "Masochist",         "desc": "Play on Hard difficulty",       "xp": 25,  "icon": "💀"},
    "no_powerup":   {"title": "Purist",            "desc": "Score 200 without power-ups",   "xp": 100, "icon": "🎯"},
    "all_modes":    {"title": "Completionist",     "desc": "Play all 4 game modes",         "xp": 150, "icon": "🗺"},
    "shield_save":  {"title": "Close Call",        "desc": "Shield saves you from death",   "xp": 60,  "icon": "🛡"},
    "daily_3":      {"title": "Dedicated",         "desc": "Complete 3 daily challenges",   "xp": 120, "icon": "📅"},
}


# ── Daily Challenges ─────────────────────────────────────────────────────────

CHALLENGE_POOL = [
    {"id": "eat_30",     "desc": "Eat 30 food items",          "goal": 30,  "stat": "food_eaten",   "xp": 80},
    {"id": "eat_60",     "desc": "Eat 60 food items",          "goal": 60,  "stat": "food_eaten",   "xp": 150},
    {"id": "score_500",  "desc": "Score 500 points",           "goal": 500, "stat": "score",        "xp": 100},
    {"id": "score_2000", "desc": "Score 2000 points",          "goal": 2000,"stat": "score",        "xp": 250},
    {"id": "combo_8",    "desc": "Achieve an 8× combo",        "goal": 8,   "stat": "max_combo",    "xp": 120},
    {"id": "survive_2m", "desc": "Survive for 2 minutes",      "goal": 120, "stat": "time_alive",   "xp": 90},
    {"id": "level_5",    "desc": "Reach level 5",              "goal": 5,   "stat": "level",        "xp": 130},
    {"id": "powerups_5", "desc": "Collect 5 power-ups",        "goal": 5,   "stat": "powerups",     "xp": 70},
    {"id": "length_30",  "desc": "Grow to length 30",          "goal": 30,  "stat": "max_length",   "xp": 85},
    {"id": "no_die_3m",  "desc": "Don't die for 3 minutes",    "goal": 180, "stat": "time_alive",   "xp": 200},
]


def _today_seed() -> int:
    d = date.today()
    return d.year * 10000 + d.month * 100 + d.day


def get_daily_challenges() -> List[dict]:
    random.seed(_today_seed())
    chosen = random.sample(CHALLENGE_POOL, min(3, len(CHALLENGE_POOL)))
    random.seed()  # reset
    return chosen


# ── Progression Manager ──────────────────────────────────────────────────────

class ProgressionManager:
    def __init__(self):
        self.data = self._load()
        self._session_achievements = []

    def _default(self) -> dict:
        return {
            "xp":                 0,
            "level":              1,
            "unlocked_skins":     ["default"],
            "achievements":       [],
            "hi_scores":          {"EASY": 0, "MEDIUM": 0, "HARD": 0},
            "total_games":        0,
            "total_food_eaten":   0,
            "total_powerups":     0,
            "modes_played":       [],
            "daily_date":         "",
            "daily_progress":     {},
            "daily_completed":    [],
            "daily_completions":  0,
        }

    def _load(self) -> dict:
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE) as f:
                    d = json.load(f)
                # Merge with defaults to handle new keys
                base = self._default()
                base.update(d)
                return base
            except Exception:
                pass
        return self._default()

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Save] Error: {e}")

    # ── XP & Level ─────────────────────────────────────────────────────────

    def add_xp(self, amount: int) -> int:
        """Returns XP added."""
        self.data["xp"] += amount
        old_level = self.data["level"]
        self.data["level"] = self._calc_player_level()
        if self.data["level"] > old_level:
            pass  # caller handles level-up notification
        return amount

    def _calc_player_level(self) -> int:
        xp = self.data["xp"]
        lvl = 1
        threshold = 200
        while xp >= threshold:
            xp -= threshold
            lvl += 1
            threshold += 50
        return lvl

    @property
    def xp(self) -> int:
        return self.data["xp"]

    @property
    def player_level(self) -> int:
        return self.data["level"]

    # ── High Scores ────────────────────────────────────────────────────────

    def update_hi_score(self, difficulty: str, score: int) -> bool:
        current = self.data["hi_scores"].get(difficulty, 0)
        if score > current:
            self.data["hi_scores"][difficulty] = score
            return True
        return False

    def hi_score(self, difficulty: str) -> int:
        return self.data["hi_scores"].get(difficulty, 0)

    @property
    def hi_scores(self) -> dict:
        return self.data["hi_scores"]

    # ── Skins ───────────────────────────────────────────────────────────────

    def unlock_skin(self, skin_key: str) -> bool:
        if skin_key not in self.data["unlocked_skins"]:
            self.data["unlocked_skins"].append(skin_key)
            return True
        return False

    def skin_unlocked(self, skin_key: str) -> bool:
        return skin_key in self.data["unlocked_skins"]

    def check_skin_unlocks(self) -> List[str]:
        from snake import SKINS
        newly_unlocked = []
        for key, skin in SKINS.items():
            if self.xp >= skin["unlock"] and not self.skin_unlocked(key):
                self.unlock_skin(key)
                newly_unlocked.append(key)
        return newly_unlocked

    # ── Achievements ───────────────────────────────────────────────────────

    def unlock_achievement(self, key: str) -> Optional[dict]:
        if key not in ACHIEVEMENTS:
            return None
        if key in self.data["achievements"]:
            return None
        self.data["achievements"].append(key)
        defn = ACHIEVEMENTS[key]
        self.add_xp(defn["xp"])
        self._session_achievements.append(key)
        return defn

    def check_achievements(self, stats: dict) -> List[dict]:
        """Check session stats and return newly unlocked achievements."""
        newly = []

        checks = [
            ("first_eat",    stats.get("food_eaten", 0) >= 1),
            ("combo_5",      stats.get("max_combo", 0) >= 5),
            ("combo_10",     stats.get("max_combo", 0) >= 10),
            ("length_20",    stats.get("max_length", 0) >= 20),
            ("length_50",    stats.get("max_length", 0) >= 50),
            ("length_100",   stats.get("max_length", 0) >= 100),
            ("score_100",    stats.get("score", 0) >= 100),
            ("score_1000",   stats.get("score", 0) >= 1000),
            ("score_5000",   stats.get("score", 0) >= 5000),
            ("level_3",      stats.get("level", 1) >= 3),
            ("level_7",      stats.get("level", 1) >= 7),
            ("powerup_10",   self.data["total_powerups"] >= 10),
            ("survive_60s",  stats.get("time_alive", 0) >= 60),
            ("survive_300s", stats.get("time_alive", 0) >= 300),
            ("hard_mode",    stats.get("difficulty") == "HARD"),
            ("shield_save",  stats.get("shield_saves", 0) >= 1),
        ]

        # All modes played
        modes_played = set(self.data.get("modes_played", []))
        if {"CLASSIC", "TIME ATTACK", "CHALLENGE", "SURVIVAL"}.issubset(modes_played):
            checks.append(("all_modes", True))

        for key, condition in checks:
            if condition:
                result = self.unlock_achievement(key)
                if result:
                    newly.append(result)

        return newly

    # ── Lifetime stats ─────────────────────────────────────────────────────

    def record_game(self, mode: str, difficulty: str, stats: dict):
        self.data["total_games"] += 1
        self.data["total_food_eaten"] += stats.get("food_eaten", 0)
        self.data["total_powerups"]   += stats.get("powerups_collected", 0)
        modes = self.data.get("modes_played", [])
        if mode not in modes:
            modes.append(mode)
        self.data["modes_played"] = modes

    # ── Daily Challenges ───────────────────────────────────────────────────

    def daily_challenges(self) -> List[dict]:
        today = str(date.today())
        if self.data.get("daily_date") != today:
            self.data["daily_date"]      = today
            self.data["daily_progress"]  = {}
            self.data["daily_completed"] = []
        return get_daily_challenges()

    def update_daily(self, stat_key: str, value) -> List[dict]:
        """Update daily challenge progress. Returns list of newly completed."""
        today = str(date.today())
        if self.data.get("daily_date") != today:
            self.daily_challenges()  # reset

        newly_completed = []
        for ch in self.daily_challenges():
            if ch["id"] in self.data["daily_completed"]:
                continue
            if ch["stat"] == stat_key:
                current = self.data["daily_progress"].get(ch["id"], 0)
                new_val = max(current, value) if stat_key in ("max_combo", "level", "max_length") else value
                self.data["daily_progress"][ch["id"]] = new_val
                if new_val >= ch["goal"]:
                    self.data["daily_completed"].append(ch["id"])
                    self.add_xp(ch["xp"])
                    self.data["daily_completions"] = self.data.get("daily_completions", 0) + 1
                    newly_completed.append(ch)
                    # Check daily achievement
                    if self.data.get("daily_completions", 0) >= 3:
                        r = self.unlock_achievement("daily_3")
                        # caller handles toast

        return newly_completed

    def daily_progress_frac(self, challenge: dict) -> float:
        cid  = challenge["id"]
        prog = self.data["daily_progress"].get(cid, 0)
        done = cid in self.data["daily_completed"]
        if done:
            return 1.0
        return min(1.0, prog / challenge["goal"])


# ── Score Combo System ───────────────────────────────────────────────────────

class ComboSystem:
    COMBO_WINDOW = 180   # frames to eat next food before combo resets (3s at 60fps)

    def __init__(self):
        self.count       = 0
        self.max_count   = 0
        self.timer       = 0
        self.multiplier  = 1.0
        self._just_hit   = False

    def reset(self):
        self.count       = 0
        self.max_count   = 0
        self.timer       = 0
        self.multiplier  = 1.0

    def eat(self) -> float:
        """Call when food is eaten. Returns score multiplier."""
        self.timer  = self.COMBO_WINDOW
        self.count += 1
        self.max_count = max(self.max_count, self.count)
        self._just_hit = True
        # Multiplier scales up: 1x, 1.5x, 2x, 2.5x … cap at 5x
        self.multiplier = min(5.0, 1.0 + (self.count - 1) * 0.25)
        return self.multiplier

    def update(self):
        self._just_hit = False
        if self.timer > 0:
            self.timer -= 1
        else:
            if self.count > 0:
                self.count      = 0
                self.multiplier = 1.0

    @property
    def active(self) -> bool:
        return self.count >= 2

    @property
    def label(self) -> str:
        if self.count >= 10:
            return f"GODLIKE  ×{self.count}"
        elif self.count >= 7:
            return f"INSANE  ×{self.count}"
        elif self.count >= 5:
            return f"HOT STREAK  ×{self.count}"
        elif self.count >= 3:
            return f"COMBO  ×{self.count}"
        elif self.count >= 2:
            return f"NICE  ×{self.count}"
        return ""

    @property
    def bar_fraction(self) -> float:
        if self.timer <= 0:
            return 0.0
        return self.timer / self.COMBO_WINDOW