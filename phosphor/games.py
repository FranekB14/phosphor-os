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
    def cmd_snake(self, args=None):
        W, H = 22, 11
        snake = [(W // 2, H // 2), (W // 2 - 1, H // 2), (W // 2 - 2, H // 2)]
        dirn = (1, 0)
        food = self._snake_food(snake, W, H)
        score = 0
        self.p("  SNAKE — w/a/s/d to steer, Enter keeps going, q to quit.", "accent")
        while True:
            self._snake_draw(snake, food, W, H, score)
            raw = self._input("  move> ", "dim")
            if raw is None:
                return
            k = raw.strip().lower()[:1]
            if k == "q":
                self.p(f"  bye — length {len(snake)}.", "dim"); return
            nd = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}.get(k)
            if nd and (nd[0] != -dirn[0] or nd[1] != -dirn[1]):
                dirn = nd
            hx, hy = snake[0]
            nx, ny = hx + dirn[0], hy + dirn[1]
            if nx < 0 or nx >= W or ny < 0 or ny >= H or (nx, ny) in snake[:-1]:
                self._snake_draw(snake, food, W, H, score)
                self._snd("gameover")
                self.p(f"  ✖ GAME OVER — length {len(snake)}, score {score}.", "err")
                if self.record_score("snake_best", score, "max"):
                    self.p("  ★ new best!", "accent")
                return
            snake.insert(0, (nx, ny))
            if (nx, ny) == food:
                score += 1
                self._snd("eat")
                food = self._snake_food(snake, W, H)
            else:
                snake.pop()

    def _snake_food(self, snake, W, H):
        empty = [(x, y) for x in range(W) for y in range(H) if (x, y) not in snake]
        return random.choice(empty) if empty else (0, 0)

    def _snake_draw(self, snake, food, W, H, score):
        self.p(f"  ┌{'─' * W}┐  score {score}", "accent")
        head, body = snake[0], set(snake[1:])
        for y in range(H):
            row = []
            for x in range(W):
                row.append("@" if (x, y) == head else
                           "o" if (x, y) in body else
                           "♦" if (x, y) == food else " ")
            self.p("  │" + "".join(row) + "│", "text")
        self.p(f"  └{'─' * W}┘", "accent")

    _TETRO = {
        "I": [(0, 0), (1, 0), (2, 0), (3, 0)], "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "T": [(0, 0), (1, 0), (2, 0), (1, 1)], "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
        "Z": [(0, 0), (1, 0), (1, 1), (2, 1)], "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
        "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
    }

    _TETRO_COLOR = {"I": (0, 240, 240), "O": (240, 240, 0), "T": (200, 0, 240),
                    "S": (0, 240, 0), "Z": (240, 0, 0), "J": (0, 0, 240), "L": (240, 160, 0)}

    def cmd_tetris(self, args=None):
        W, H = 10, 16
        well = [[None] * W for _ in range(H)]

        def collides(cells, ox, oy):
            for cx, cy in cells:
                x, y = ox + cx, oy + cy
                if x < 0 or x >= W or y >= H:
                    return True
                if y >= 0 and well[y][x] is not None:
                    return True
            return False

        def rotate(cells):
            r = [(-cy, cx) for cx, cy in cells]
            mnx, mny = min(c[0] for c in r), min(c[1] for c in r)
            return [(cx - mnx, cy - mny) for cx, cy in r]

        def spawn():
            key = random.choice(list(self._TETRO))
            return list(self._TETRO[key]), 3, 0, self._TETRO_COLOR[key]

        cells, ox, oy, color = spawn()
        score, lines = 0, 0
        self.p("  TETRIS — a/d move · w rotate · s/Enter drop one · p hard-drop · q quit.", "accent")
        while True:
            self._tetris_draw(well, cells, ox, oy, color, score, lines, W, H)
            raw = self._input("  > ", "dim")
            if raw is None:
                return
            s = raw.strip().lower()
            c = s[:1] if s else "s"
            if c == "q":
                self.p(f"  bye — {lines} lines, score {score}.", "dim"); return
            if c == "a":
                if not collides(cells, ox - 1, oy):
                    ox -= 1
            elif c == "d":
                if not collides(cells, ox + 1, oy):
                    ox += 1
            elif c == "w":
                r = rotate(cells)
                if not collides(r, ox, oy):
                    cells = r
            else:                                  # drop: s/Enter = one row, p = hard
                if c == "p":
                    while not collides(cells, ox, oy + 1):
                        oy += 1
                elif not collides(cells, ox, oy + 1):
                    oy += 1
                if collides(cells, ox, oy + 1):    # resting -> lock it
                    for cx, cy in cells:
                        if 0 <= oy + cy < H:
                            well[oy + cy][ox + cx] = color
                    kept = [row for row in well if any(v is None for v in row)]
                    cleared = H - len(kept)
                    if cleared:
                        lines += cleared
                        score += (0, 40, 100, 300, 1200)[min(cleared, 4)]
                        well = [[None] * W for _ in range(cleared)] + kept
                        self._snd("line")
                    cells, ox, oy, color = spawn()
                    if collides(cells, ox, oy):
                        self._tetris_draw(well, cells, ox, oy, color, score, lines, W, H)
                        self._snd("gameover")
                        self.p(f"  ✖ GAME OVER — {lines} lines, score {score}.", "err")
                        if self.record_score("tetris_best", score, "max"):
                            self.p("  ★ new best!", "accent")
                        return

    def _tetris_draw(self, well, cells, ox, oy, color, score, lines, W, H):
        overlay = {(ox + cx, oy + cy): color for cx, cy in cells}
        self.p(f"  ╔{'══' * W}╗   lines {lines}  score {score}", "accent")
        for y in range(H):
            row = "  ║"
            for x in range(W):
                col = overlay.get((x, y)) or well[y][x]
                row += (rgb(*col) + "██" + RESET) if col else self.c(" .", "dim")
            print(row + self.c("║", "accent"))
        self.p(f"  ╚{'══' * W}╝", "accent")

    def cmd_solitaire(self, args=None):
        ranks = {1: "A", 11: "J", 12: "Q", 13: "K"}

        def red(su):
            return su in (1, 2)

        def cstr(card):
            rk, su, up = card
            if not up:
                return "##"
            txt = f"{ranks.get(rk, str(rk))}{'♠♥♦♣'[su]}"
            return (rgb(255, 90, 90) + txt + RESET) if red(su) else txt

        deck = [(rk, su, False) for su in range(4) for rk in range(1, 14)]
        random.shuffle(deck)
        tableau = [[] for _ in range(7)]
        for i in range(7):
            for j in range(i + 1):
                c = deck.pop()
                tableau[i].append((c[0], c[1], j == i))
        stock = [(c[0], c[1], False) for c in deck]
        waste, found = [], [[] for _ in range(4)]

        def can_tab(card, dest):
            if not dest:
                return card[0] == 13
            top = dest[-1]
            return top[2] and (red(card[1]) != red(top[1])) and card[0] == top[0] - 1

        def can_found(card, su):
            pile = found[su]
            return card[1] == su and ((not pile and card[0] == 1) or
                                      (pile and card[0] == pile[-1][0] + 1))

        def flip(p):
            if p and not p[-1][2]:
                t = p[-1]; p[-1] = (t[0], t[1], True)

        def board():
            self.p("", "text")
            f = "  ".join((cstr(found[s][-1]) if found[s] else "·" + "♠♥♦♣"[s]) for s in range(4))
            self.p(f"  stock:{len(stock):>2}   waste: {cstr(waste[-1]) if waste else '--'}"
                   f"      foundations: {f}", "accent")
            self.p("  " + "─" * 52, "dim")
            for i, pile in enumerate(tableau):
                self.p(f"  {i + 1}: " + (" ".join(cstr(c) for c in pile) if pile else "·"), "text")

        self.p("  KLONDIKE SOLITAIRE", "accent")
        self.p("  moves: draw | wf (waste→foundation) | w3 (waste→pile 3) |", "dim")
        self.p("         25 (pile 2→pile 5) | 3f (pile 3→foundation) | q quit", "dim")
        while True:
            board()
            if all(len(found[s]) == 13 for s in range(4)):
                self._snd("win")
                self.p("  ★★★ YOU WIN — all 52 cards home! ★★★", "accent")
                self.record_score("solitaire_wins", 1, "count")
                return
            raw = self._input("  move> ", "dim")
            if raw is None:
                return
            m = raw.strip().lower().replace(" ", "")
            if m in ("q", "quit"):
                self.p("  game abandoned.", "dim"); return
            if m in ("d", "draw"):
                if stock:
                    c = stock.pop(); waste.append((c[0], c[1], True))
                elif waste:
                    stock[:] = [(c[0], c[1], False) for c in reversed(waste)]; waste.clear()
                else:
                    self.p("  nothing to draw.", "warn")
                continue
            if m == "wf":
                if waste and can_found(waste[-1], waste[-1][1]):
                    found[waste[-1][1]].append(waste.pop())
                else:
                    self.p("  illegal move.", "err")
                continue
            if len(m) == 2 and m[0] == "w" and m[1].isdigit():
                d = int(m[1]) - 1
                if waste and 0 <= d < 7 and can_tab(waste[-1], tableau[d]):
                    tableau[d].append(waste.pop())
                else:
                    self.p("  illegal move.", "err")
                continue
            if len(m) == 2 and m[0].isdigit() and m[1] == "f":
                a = int(m[0]) - 1
                if 0 <= a < 7 and tableau[a] and tableau[a][-1][2] and can_found(tableau[a][-1], tableau[a][-1][1]):
                    found[tableau[a][-1][1]].append(tableau[a].pop()); flip(tableau[a])
                else:
                    self.p("  illegal move.", "err")
                continue
            if len(m) == 2 and m[0].isdigit() and m[1].isdigit():
                a, b = int(m[0]) - 1, int(m[1]) - 1
                if 0 <= a < 7 and 0 <= b < 7 and tableau[a]:
                    fu = [i for i, c in enumerate(tableau[a]) if c[2]]
                    start = fu[0] if fu else len(tableau[a])
                    moved = tableau[a][start:]
                    if moved and can_tab(moved[0], tableau[b]):
                        tableau[b].extend(moved); del tableau[a][start:]; flip(tableau[a])
                    else:
                        self.p("  illegal move.", "err")
                else:
                    self.p("  illegal move.", "err")
                continue
            self.p("  ? unknown move — try: draw, wf, w3, 3f, 25, q", "warn")

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
