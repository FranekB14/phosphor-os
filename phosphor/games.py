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
