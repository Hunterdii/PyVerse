#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Number Duel — a "cool" number game with multiple modes, hints, scoring, and highscores.
Place this file in Number-Duel-Game/ and run:
    python Number-Duel-Game/number_duel.py

Features:
- Single-player guess-the-number with difficulty levels.
- Timed mode (optional) and limited attempts mode.
- Hints (higher/lower, "close" ranges, digit matches).
- Score calculation and persistent highscores stored in highscores.json.
- Clean input validation and friendly UI (ASCII headers).
"""

from datetime import datetime
from pathlib import Path
import json
import random
import time

# ----------------------------
# Config / constants
# ----------------------------
GAME_DIR = Path(__file__).resolve().parent
HIGHSCORE_FILE = GAME_DIR / "highscores.json"

DIFFICULTIES = {
    "easy":    {"min": 1, "max": 50,  "attempts": 10, "time_limit": None},
    "medium":  {"min": 1, "max": 200, "attempts": 8,  "time_limit": None},
    "hard":    {"min": 1, "max": 1000,"attempts": 10, "time_limit": None},
    "timed":   {"min": 1, "max": 500, "attempts": None, "time_limit": 20},  # seconds per round
}

# ----------------------------
# Utilities: highscores
# ----------------------------
def load_highscores():
    if not HIGHSCORE_FILE.exists():
        return []
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_highscores(entries):
    with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

def add_highscore(name, score, difficulty):
    entries = load_highscores()
    entries.append({
        "name": name,
        "score": score,
        "difficulty": difficulty,
        "date": datetime.utcnow().isoformat() + "Z"
    })
    # keep highest scores on top (higher is better)
    entries = sorted(entries, key=lambda e: e["score"], reverse=True)[:50]
    save_highscores(entries)

def display_highscores(limit=10):
    entries = load_highscores()
    if not entries:
        print("No highscores yet — be the first!")
        return
    print("\n🏆 Top Highscores")
    for i, e in enumerate(entries[:limit], start=1):
        dt = e.get("date", "")[:19].replace("T", " ")
        print(f"{i}. {e['name']} — {e['score']} pts ({e['difficulty']}) on {dt}")
    print()

# ----------------------------
# Game core
# ----------------------------
def header():
    print("="*60)
    print("🎯 Number Duel — guess the secret number!".center(60))
    print("="*60)

def choose_difficulty():
    print("Choose difficulty / mode:")
    for k in DIFFICULTIES:
        d = DIFFICULTIES[k]
        desc = f"{k.title()}: {d['min']}–{d['max']}"
        if d["attempts"]:
            desc += f", attempts: {d['attempts']}"
        if d["time_limit"]:
            desc += f", time limit: {d['time_limit']}s"
        print(f"  - {k}  -> {desc}")
    while True:
        pick = input("Enter difficulty (easy/medium/hard/timed): ").strip().lower()
        if pick in DIFFICULTIES:
            return pick
        print("Invalid choice. Try again.")

def get_int(prompt, min_val=None, max_val=None):
    while True:
        s = input(prompt).strip()
        if not s:
            print("Please enter a number.")
            continue
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            n = int(s)
            if min_val is not None and n < min_val:
                print(f"Number must be at least {min_val}.")
                continue
            if max_val is not None and n > max_val:
                print(f"Number must be at most {max_val}.")
                continue
            return n
        print("That's not a valid integer. Try again.")

def give_hint(secret, guess, attempt, max_attempts):
    # Basic higher/lower hint
    diff = abs(secret - guess)
    if diff == 0:
        return "Correct!"
    if diff <= max(1, (secret * 0.02 if secret else 2)):
        basic = "You're extremely close!"
    elif diff <= 3:
        basic = "Very close."
    elif diff <= 10:
        basic = "Close."
    else:
        basic = "Not that close."

    hl = "higher" if guess < secret else "lower"
    digit_hint = ""
    # Digit-match hint when numbers are small-ish
    if secret < 10000 and guess < 10000:
        secret_s = str(secret)
        guess_s = str(guess)
        matches = sum(1 for a,b in zip(secret_s[::-1], guess_s[::-1]) if a==b)
        if matches:
            digit_hint = f" (Digits from right matched: {matches})"
    return f"{basic} Try {hl}.{digit_hint}"

def play_round(difficulty_key, player_name):
    cfg = DIFFICULTIES[difficulty_key]
    lo, hi = cfg["min"], cfg["max"]
    secret = random.randint(lo, hi)
    attempts_left = cfg["attempts"]
    time_limit = cfg["time_limit"]
    start_time = time.time()

    print(f"\nI've picked a number between {lo} and {hi}. Good luck, {player_name}!")
    if attempts_left:
        print(f"You have {attempts_left} attempts.")
    if time_limit:
        print(f"You have {time_limit} seconds to guess. Timer starts on your first guess.")

    guesses = []
    while True:
        # time check
        if time_limit:
            elapsed = time.time() - start_time
            remain = max(0, time_limit - elapsed)
            if elapsed > time_limit:
                print("\n⏱ Time's up!")
                return {"win": False, "attempts": len(guesses), "secret": secret}
            print(f"[Timer: {int(remain)}s left]", end=" ")

        # attempts check
        if attempts_left is not None and attempts_left <= 0:
            print("\nNo attempts left!")
            return {"win": False, "attempts": len(guesses), "secret": secret}

        # read guess safely
        guess = get_int("Your guess: ", min_val=lo, max_val=hi)
        guesses.append(guess)

        if guess == secret:
            print("\n🎉 That's correct! Well done!")
            return {"win": True, "attempts": len(guesses), "secret": secret}

        # helpful feedback
        # show higher/lower and a closeness hint
        mh = give_hint(secret, guess, len(guesses), cfg["attempts"] or 999)
        print(f"✳ {mh}")

        # reduce attempt only if attempts are being used
        if attempts_left is not None:
            attempts_left -= 1
            print(f"Attempts left: {attempts_left}")

        # offer a small strategic tip after a few wrong tries
        if len(guesses) == 3:
            # median hint: tell if secret in lower or upper half of range
            mid = (lo + hi) // 2
            half = "lower" if secret <= mid else "upper"
            print(f"💡 Tip: The secret is in the {half} half of the full range ({lo}-{hi}).")

def compute_score(result, difficulty_key):
    base = {"easy": 50, "medium": 120, "hard": 300, "timed": 200}[difficulty_key]
    if not result["win"]:
        return 0
    # fewer attempts -> larger score; quick wins in timed mode give bonus
    attempts = result["attempts"]
    score = max(10, base + max(0, (50 - attempts * 5)))
    return score

# ----------------------------
# Main menu and loop
# ----------------------------
def main():
    header()
    player = input("Enter your player name (or hit Enter for 'Player1'): ").strip() or "Player1"

    while True:
        print("\nMain Menu:")
        print(" 1) Play a round")
        print(" 2) View Highscores")
        print(" 3) How to play")
        print(" 4) Quit")
        choice = input("Choose 1-4: ").strip()
        if choice == "1":
            difficulty = choose_difficulty()
            result = play_round(difficulty, player)
            score = compute_score(result, difficulty)
            print(f"\nResult: {'WIN' if result['win'] else 'LOSS'} — Score: {score}")
            if result.get("secret") is not None and not result["win"]:
                print(f"The secret number was: {result['secret']}")
            # store highscore if win and score > 0
            if score > 0:
                add_highscore(player, score, difficulty)
                print("Highscore saved! Check the highscores from the menu.")
        elif choice == "2":
            display_highscores()
        elif choice == "3":
            print("\nHow to play:")
            print("- Select a difficulty. The game picks a secret integer in that range.")
            print("- Attempt to guess it. The game gives hints and tracks attempts/time.")
            print("- Score is awarded for correct answers; higher score for harder modes and fewer attempts.")
            print("- Highscores are saved locally in highscores.json.")
        elif choice == "4":
            print("Thanks for playing — goodbye!")
            break
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted — exiting. Goodbye!")
