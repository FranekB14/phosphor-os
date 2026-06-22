"""GamesMixin: the `games` command group."""

import os
import sys
import re
import io
import json
import time
import random
import shlex
import shutil
import fnmatch
import zipfile
import tempfile
import datetime
import textwrap
import platform
import subprocess
import urllib.request
import urllib.error

from . import runtime
from .constants import *
from .helpers import *


class GamesMixin:
    def cmd_guess(self, args=None):
        target = random.randint(1, 100)
        tries = 0
        self.p("  I'm thinking of a number from 1 to 100.", "accent")
        self.p("  Type a guess (or 'q' to quit).", "dim")
        while True:
            raw = self._input("  guess> ")
            if raw is None or raw.strip().lower() in ("q", "quit", "exit"):
                self.p(f"  The number was {target}. Bye!", "dim"); return
            try:
                g = int(raw.strip())
            except ValueError:
                self.p("  enter a whole number.", "err"); continue
            tries += 1
            if g < target:
                self.p("  ↑ higher", "text")
            elif g > target:
                self.p("  ↓ lower", "text")
            else:
                best = self.record_score("guess_best", tries, "min")
                self.p(f"  ✦ got it in {tries} tries! ✦" + ("  (new best!)" if best else ""), "warn"); return

    def cmd_rps(self, args=None):
        beats = {"r": "s", "p": "r", "s": "p"}
        names = {"r": "rock", "p": "paper", "s": "scissors"}
        me = you = 0
        self.p("  Rock-Paper-Scissors — first to 3 wins.", "accent")
        while me < 3 and you < 3:
            raw = self._input("  [r]ock [p]aper [s]cissors (q quit)> ")
            if raw is None:
                return
            pick = raw.strip().lower()[:1]
            if pick == "q":
                self.p("  game abandoned.", "dim"); return
            if pick not in beats:
                self.p("  pick r, p, or s.", "err"); continue
            cpu = random.choice("rps")
            if pick == cpu:
                result = "tie"
            elif beats[pick] == cpu:
                result = "win"; you += 1
            else:
                result = "lose"; me += 1
            self.p(f"  you: {names[pick]:<8} cpu: {names[cpu]:<8} -> {result.upper()}  "
                   f"(you {you} - {me} cpu)", "text")
        if you > me:
            self.record_score("rps_wins", 1, "count")
        self.p("  ✦ you win the match! ✦" if you > me else "  the computer wins. rematch?",
               "warn" if you > me else "dim")

    _HANGMAN_WORDS = ["python", "phosphor", "kernel", "binary", "matrix",
                      "cursor", "pixel", "syntax", "buffer", "packet",
                      "compile", "terminal", "function", "variable"]

    _GALLOWS = [
        " +---+\n     |\n     |\n     |\n    ===",
        " +---+\n O   |\n     |\n     |\n    ===",
        " +---+\n O   |\n |   |\n     |\n    ===",
        " +---+\n O   |\n/|   |\n     |\n    ===",
        " +---+\n O   |\n/|\\  |\n     |\n    ===",
        " +---+\n O   |\n/|\\  |\n/    |\n    ===",
        " +---+\n O   |\n/|\\  |\n/ \\  |\n    ===",
    ]

    def cmd_hangman(self, args=None):
        word = random.choice(self._HANGMAN_WORDS)
        guessed, wrong = set(), 0
        self.p("  Hangman! Guess one letter at a time.", "accent")
        while wrong < len(self._GALLOWS) - 1:
            shown = " ".join(ch if ch in guessed else "_" for ch in word)
            for line in self._GALLOWS[wrong].splitlines():
                self.p("  " + line, "warn")
            self.p("  word: " + shown, "text")
            if all(ch in guessed for ch in word):
                self.record_score("hangman_wins", 1, "count")
                self.p("  ✦ solved it! ✦", "warn"); return
            raw = self._input("  letter> ")
            if raw is None:
                return
            g = raw.strip().lower()[:1]
            if not g.isalpha():
                self.p("  letters only.", "err"); continue
            if g in guessed:
                self.p("  already tried that.", "dim"); continue
            guessed.add(g)
            if g not in word:
                wrong += 1
                self.p(f"  no '{g}'. wrong guesses: {wrong}", "err")
        for line in self._GALLOWS[-1].splitlines():
            self.p("  " + line, "err")
        self.p(f"  game over — the word was '{word}'.", "dim")

    def cmd_ttt(self, args=None):
        b = [str(i) for i in range(1, 10)]
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

        def draw():
            for r in range(0, 9, 3):
                self.p(f"   {b[r]} │ {b[r+1]} │ {b[r+2]} ", "text")
                if r < 6:
                    self.p("  ───┼───┼───", "dim")

        def winner(p):
            return any(all(b[i] == p for i in line) for line in wins)

        def cpu_move():
            for p in ("O", "X"):                      # take the win, else block
                for line in wins:
                    cells = [b[i] for i in line]
                    if cells.count(p) == 2:
                        for i in line:
                            if b[i].isdigit():
                                return i
            if b[4].isdigit():                        # prefer the centre
                return 4
            free = [i for i in range(9) if b[i].isdigit()]
            return random.choice(free)

        self.p("  Tic-Tac-Toe — you are X. Enter 1-9.", "accent")
        draw()
        moves = 0
        while moves < 9:
            raw = self._input("  your move> ")
            if raw is None:
                return
            mv = raw.strip()
            if not (mv.isdigit() and mv in b):
                self.p("  pick a free number.", "err"); continue
            b[int(mv) - 1] = "X"; moves += 1
            draw()
            if winner("X"):
                self.record_score("ttt_wins", 1, "count")
                self.p("  ✦ you win! ✦", "warn"); return
            if moves >= 9:
                break
            b[cpu_move()] = "O"; moves += 1
            self.p("  computer plays:", "dim"); draw()
            if winner("O"):
                self.p("  computer wins.", "err"); return
        self.p("  it's a draw.", "dim")

    _QUIZ = [
        ("What does CPU stand for?",
         ["Central Process Unit", "Central Processing Unit", "Computer Personal Unit"], 2),
        ("Which base does hexadecimal use?", ["8", "10", "16"], 3),
        ("What year was Python first released?", ["1991", "2000", "1985"], 1),
        ("How many bits in a byte?", ["4", "8", "16"], 2),
        ("What does 'RAM' stand for?",
         ["Random Access Memory", "Rapid Active Module", "Read Adjusted Memory"], 1),
    ]

    def cmd_quiz(self, args=None):
        qs = random.sample(self._QUIZ, len(self._QUIZ))
        score = 0
        self.p("  Trivia time! Type the option number.", "accent")
        for n, (q, opts, ans) in enumerate(qs, 1):
            self.p(f"\n  {n}. {q}", "text")
            for i, o in enumerate(opts, 1):
                self.p(f"     {i}) {o}", "dim")
            raw = self._input("  answer> ")
            if raw is None:
                self.p("  quiz ended early.", "dim"); break
            if raw.strip() == str(ans):
                self.p("  ✓ correct!", "warn"); score += 1
            else:
                self.p(f"  ✗ nope — it was {ans}) {opts[ans-1]}", "err")
        self.record_score("quiz_best", score, "max")
        self.p(f"\n  final score: {score}/{len(qs)}", "accent")

    _WORDS = ["crane", "pixel", "ghost", "robot", "lemon", "vivid", "wharf",
              "joker", "fjord", "quilt", "mango", "nerdy", "byte", "glyph"]

    def cmd_wordle(self, args=None):
        answer = random.choice([w for w in self._WORDS if len(w) == 5])
        self.p("  Guess the 5-letter word. 6 tries.", "accent")
        self.p("  [#]=right spot  [+]=wrong spot  [.]=not in word", "dim")
        for attempt in range(6):
            raw = self._input(f"  try {attempt+1}/6> ")
            if raw is None:
                self.p(f"  the word was '{answer}'.", "dim"); return
            guess = raw.strip().lower()
            if len(guess) != 5 or not guess.isalpha():
                self.p("  need a 5-letter word.", "err"); continue
            marks = []
            for i, ch in enumerate(guess):
                if ch == answer[i]:
                    marks.append(self.c(ch.upper(), "warn"))
                elif ch in answer:
                    marks.append(self.c(ch, "accent"))
                else:
                    marks.append(self.c(ch, "dim"))
            print("  " + " ".join(marks))
            if guess == answer:
                self.record_score("wordle_best", attempt + 1, "min")
                self.p("  ✦ brilliant! ✦", "warn"); return
        self.p(f"  out of tries — the word was '{answer}'.", "dim")

    def cmd_2048(self, args=None):
        size = 4
        grid = [[0] * size for _ in range(size)]
        score = 0

        def spawn():
            empties = [(r, c) for r in range(size) for c in range(size) if grid[r][c] == 0]
            if empties:
                r, c = random.choice(empties)
                grid[r][c] = 4 if random.random() < 0.1 else 2

        def draw():
            print()
            for row in grid:
                self.p("  " + "".join(f"{(str(v) if v else '.'):>6}" for v in row), "accent")
            self.p(f"  score: {score}", "dim")

        def compress(line):
            nums = [x for x in line if x]
            out, gained, i = [], 0, 0
            while i < len(nums):
                if i + 1 < len(nums) and nums[i] == nums[i + 1]:
                    out.append(nums[i] * 2); gained += nums[i] * 2; i += 2
                else:
                    out.append(nums[i]); i += 1
            return out + [0] * (size - len(out)), gained

        def move(direction):
            nonlocal score
            moved = False
            for i in range(size):
                if direction in ("a", "d"):
                    line = grid[i][::-1] if direction == "d" else grid[i][:]
                    new, g = compress(line)
                    if direction == "d":
                        new = new[::-1]
                    if new != grid[i]:
                        grid[i] = new; moved = True
                    score += g
                else:
                    col = [grid[r][i] for r in range(size)]
                    if direction == "s":
                        col = col[::-1]
                    new, g = compress(col)
                    if direction == "s":
                        new = new[::-1]
                    for r in range(size):
                        if grid[r][i] != new[r]:
                            moved = True
                        grid[r][i] = new[r]
                    score += g
            return moved

        def can_move():
            if any(0 in row for row in grid):
                return True
            for r in range(size):
                for c in range(size):
                    if c + 1 < size and grid[r][c] == grid[r][c + 1]:
                        return True
                    if r + 1 < size and grid[r][c] == grid[r + 1][c]:
                        return True
            return False

        spawn(); spawn()
        self.p("  2048 — combine tiles. w/a/s/d to slide, q to quit.", "accent")
        won = False
        while True:
            draw()
            if any(2048 in row for row in grid) and not won:
                self.p("  ★ you reached 2048! keep going or press q. ★", "warn")
                won = True
            raw = self._input("  move> ")
            if raw is None or raw.strip().lower().startswith("q"):
                self.record_score("2048_best", score, "max")
                self.p(f"  final score: {score}", "dim"); return
            d = raw.strip().lower()[:1]
            if d not in "wasd":
                self.p("  use w / a / s / d.", "err"); continue
            if move(d):
                spawn()
                if not can_move():
                    draw()
                    self.record_score("2048_best", score, "max")
                    self.p("  no moves left — game over!", "err"); return
            else:
                self.p("  (no change — try another direction)", "dim")

    def cmd_minesweeper(self, args=None):
        W = H = 9
        MINES = 10
        mines = set()
        while len(mines) < MINES:
            mines.add((random.randrange(H), random.randrange(W)))
        revealed, flags = set(), set()

        def count(r, c):
            return sum((rr, cc) in mines
                       for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                       if (rr, cc) != (r, c))

        def draw(reveal_all=False):
            self.p("     " + " ".join(str(c + 1) for c in range(W)), "dim")
            for r in range(H):
                cells = []
                for c in range(W):
                    if (r, c) in flags and not reveal_all:
                        cells.append("F")
                    elif (r, c) not in revealed and not reveal_all:
                        cells.append("·")
                    elif (r, c) in mines:
                        cells.append("*")
                    else:
                        n = count(r, c)
                        cells.append(str(n) if n else " ")
                self.p(f"  {r + 1:>2} " + " ".join(cells), "text")

        def flood(r, c):
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if not (0 <= cr < H and 0 <= cc < W):
                    continue
                if (cr, cc) in revealed or (cr, cc) in mines:
                    continue
                revealed.add((cr, cc))
                if count(cr, cc) == 0:
                    for rr in range(cr - 1, cr + 2):
                        for cc2 in range(cc - 1, cc + 2):
                            stack.append((rr, cc2))

        self.p("  Minesweeper — 9x9, 10 mines.", "accent")
        self.p("  reveal: 'row col'   flag: 'f row col'   quit: q", "dim")
        while True:
            draw()
            raw = self._input("  > ")
            if raw is None or raw.strip().lower().startswith("q"):
                self.p("  game abandoned.", "dim"); return
            parts = raw.strip().lower().split()
            flagging = bool(parts) and parts[0] in ("f", "flag")
            if flagging:
                parts = parts[1:]
            if len(parts) < 2 or not (parts[0].isdigit() and parts[1].isdigit()):
                self.p("  enter: row col   (e.g. 3 5)", "err"); continue
            r, c = int(parts[0]) - 1, int(parts[1]) - 1
            if not (0 <= r < H and 0 <= c < W):
                self.p("  out of range.", "err"); continue
            if flagging:
                flags.discard((r, c)) if (r, c) in flags else flags.add((r, c))
                continue
            if (r, c) in mines:
                draw(reveal_all=True)
                self.p("  * BOOM — you hit a mine. *", "err"); return
            flood(r, c)
            if W * H - len(revealed) == MINES:
                draw(reveal_all=True)
                self.record_score("minesweeper_wins", 1, "count")
                self.p("  ✦ field cleared — you win! ✦", "warn"); return

    def cmd_blackjack(self, args=None):
        def card():
            return random.randint(1, 13)

        def show(c):
            return {1: "A", 11: "J", 12: "Q", 13: "K"}.get(c, str(c))

        def total(cards):
            t, aces = 0, 0
            for c in cards:
                if c == 1:
                    aces += 1; t += 11
                else:
                    t += min(c, 10)
            while t > 21 and aces:
                t -= 10; aces -= 1
            return t

        player, dealer = [card(), card()], [card(), card()]
        self.p("  Blackjack — get close to 21 without going over.", "accent")
        while True:
            self.p(f"  you: {[show(c) for c in player]} = {total(player)}", "text")
            self.p(f"  dealer shows: {show(dealer[0])}", "dim")
            if total(player) == 21:
                self.p("  21!", "warn"); break
            raw = self._input("  [h]it or [s]tand? ")
            if raw is None:
                return
            ch = raw.strip().lower()[:1]
            if ch == "h":
                player.append(card())
                if total(player) > 21:
                    self.p(f"  you: {[show(c) for c in player]} = {total(player)} — BUST!", "err")
                    return
            elif ch == "s":
                break
            else:
                self.p("  press h or s.", "err")
        while total(dealer) < 17:
            dealer.append(card())
        pv, dv = total(player), total(dealer)
        self.p(f"  dealer: {[show(c) for c in dealer]} = {dv}", "text")
        if dv > 21 or pv > dv:
            self.record_score("blackjack_wins", 1, "count")
            self.p("  ✦ you win! ✦", "warn")
        elif pv == dv:
            self.p("  push — it's a tie.", "dim")
        else:
            self.p("  dealer wins. better luck next deal.", "err")
