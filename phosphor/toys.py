"""ToysMixin: the `toys` command group."""

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


class ToysMixin:
    def cmd_matrix(self, args=None):
        args = args or []
        frames = 60
        if args and args[0].isdigit():
            frames = min(int(args[0]), 500)
        if not runtime.INTERACTIVE:
            frames = min(frames, 5)
        cols = 70
        chars = "01ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜｲｸ@#$%&*"
        try:
            for _ in range(frames):
                line = "".join(random.choice(chars) if random.random() > 0.25 else " "
                               for _ in range(cols))
                self.p(line, "text")
                if runtime.INTERACTIVE:
                    time.sleep(0.04)
        except KeyboardInterrupt:
            print()

    def cmd_hack(self, args):
        target = args[0] if args else "mainframe"
        steps = [
            f"establishing uplink to {target}...",
            "bypassing firewall [████████████] done",
            "cracking SHA-256 .... 0x4f8a2b... MATCHED",
            "injecting payload via port 1337...",
            "escalating privileges -> ROOT",
            "downloading secret_files.zip [100%]",
            "wiping logs... covering tracks...",
        ]
        for s in steps:
            self.p("  > " + s, "text")
            if runtime.INTERACTIVE:
                time.sleep(0.35)
        self.p("  ✓ ACCESS GRANTED  (just kidding — this is pretend!)", "accent")

    def cmd_cowsay(self, args):
        msg = " ".join(args) or "moo"
        top = " " + "_" * (len(msg) + 2)
        bot = " " + "-" * (len(msg) + 2)
        cow = r"""
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||"""
        self.p("  " + top, "text")
        self.p(f"  < {msg} >", "accent")
        self.p("  " + bot, "text")
        for line in cow.splitlines():
            self.p("  " + line, "text")

    FORTUNES = [
        "The best way to predict the future is to compile it.",
        "A clean disk is a sign of a wasted weekend.",
        "There are 10 kinds of people: those who read binary and those who don't.",
        "Phosphor never forgets — but the cache might.",
        "Real programmers count from zero.",
        "When in doubt, blame the cosmic rays.",
        "404: fortune not found. Have this one instead.",
        "The cake is a lie, but the segfault is real.",
        "Today is a good day to back up your data.",
        "A bug in the hand is worth two in the backlog.",
    ]

    def cmd_fortune(self, args=None):
        self.p("  ☉ " + random.choice(self.FORTUNES), "accent")

    def cmd_glitch(self, args):
        text = " ".join(args) or "PHOSPHOR"
        glitch_chars = "▓▒░#@%&"
        out = []
        for ch in text:
            if ch != " " and random.random() < 0.3:
                out.append(random.choice(glitch_chars))
            else:
                out.append(ch)
        self.p("  " + "".join(out), "err")
        self.p("  " + text, "accent")

    _8BALL = [
        "It is certain.", "Without a doubt.", "Yes, definitely.",
        "Most likely.", "Signs point to yes.", "Reply hazy, try again.",
        "Ask again later.", "Cannot predict now.", "Don't count on it.",
        "My sources say no.", "Very doubtful.", "Outlook not so good.",
    ]

    def cmd_eightball(self, args):
        if not args:
            self.p("  ask a question, e.g. 8ball will it rain?", "warn"); return
        self.p("  🎱 ".replace("🎱", "(8)") + random.choice(self._8BALL), "accent")

    _JOKES = [
        ("Why do programmers prefer dark mode?", "Because light attracts bugs."),
        ("How many programmers to change a light bulb?", "None, that's a hardware problem."),
        ("Why did the developer go broke?", "Because he used up all his cache."),
        ("What's a programmer's favorite hangout?", "The Foo Bar."),
        ("Why was the function sad after a date?", "It never got a callback."),
        ("There are 10 types of people in this world:", "those who get binary and those who don't."),
        ("Why do Java developers wear glasses?", "Because they can't C#."),
    ]

    def cmd_joke(self, args=None):
        setup, punch = random.choice(self._JOKES)
        self.p("  " + setup, "text")
        if runtime.INTERACTIVE:
            time.sleep(0.9)
        self.p("  " + punch, "accent")

    def cmd_rainbow(self, args):
        text = " ".join(args) or "PHOSPHOR-OS"
        palette = [(255, 80, 80), (255, 170, 60), (255, 240, 80),
                   (80, 255, 120), (80, 200, 255), (170, 110, 255)]
        out = []
        for i, ch in enumerate(text):
            r, g, b = palette[i % len(palette)]
            out.append(f"{rgb(r, g, b)}{ch}")
        print("  " + "".join(out) + RESET)

    def cmd_slot(self, args=None):
        reels = "🍒🔔⭐7$♦♣".replace("🍒", "C").replace("🔔", "B")
        symbols = list("$★7♦♣♥▓")
        self.p("  ┌─────────────┐", "accent")
        spins = 12 if runtime.INTERACTIVE else 1
        final = [random.choice(symbols) for _ in range(3)]
        for s in range(spins):
            row = final if s == spins - 1 else [random.choice(symbols) for _ in range(3)]
            line = "  │  " + "  ".join(row) + "  │"
            if runtime.INTERACTIVE:
                print("\r" + self.c(line, "text"), end="", flush=True)
                time.sleep(0.08)
            else:
                self.p(line, "text")
        if runtime.INTERACTIVE:
            print()
        self.p("  └─────────────┘", "accent")
        if final[0] == final[1] == final[2]:
            self.p("  ✦✦✦  JACKPOT!  ✦✦✦", "warn")
        elif len(set(final)) == 2:
            self.p("  two of a kind — nice!", "accent")
        else:
            self.p("  no match. spin again!", "dim")

    def cmd_fire(self, args=None):
        args = args or []
        frames = int(args[0]) if args and args[0].isdigit() else 40
        if not runtime.INTERACTIVE:
            frames = 3
        frames = min(frames, 400)
        palette = "  ...:::***###"
        try:
            for frame in range(frames):
                rows = []
                for y in range(6, 0, -1):
                    width = y * 2 + 1
                    cells = []
                    for _ in range(width):
                        heat = random.random() * (y / 6) + (1 - y / 6) * 0.4
                        cells.append(palette[min(len(palette) - 1, int(heat * len(palette)))])
                    rows.append(("".join(cells)).center(15))
                if runtime.INTERACTIVE and frame:
                    print("\033[6A", end="")  # move up to overwrite previous frame
                for r in rows:
                    self.p("  " + r, "warn")
                if runtime.INTERACTIVE:
                    time.sleep(0.09)
        except KeyboardInterrupt:
            pass
        self.p("  ~ a cozy little fire ~", "dim")

    def cmd_aquarium(self, args=None):
        args = args or []
        frames = int(args[0]) if args and args[0].isdigit() else 30
        if not runtime.INTERACTIVE:
            frames = 3
        frames = min(frames, 400)
        W = 40
        fish = [{"x": random.randint(0, W), "y": random.randint(0, 4),
                 "d": random.choice([-1, 1])} for _ in range(4)]
        shapes = {1: "><>", -1: "<><"}
        try:
            for f in range(frames):
                grid = [[" "] * W for _ in range(5)]
                for fl in fish:
                    fl["x"] += fl["d"]
                    if fl["x"] < 0 or fl["x"] >= W - 3:
                        fl["d"] *= -1
                        fl["x"] = max(0, min(W - 3, fl["x"]))
                    s = shapes[fl["d"]]
                    for i, ch in enumerate(s):
                        if 0 <= fl["x"] + i < W:
                            grid[fl["y"]][fl["x"] + i] = ch
                if runtime.INTERACTIVE and f:
                    print("\033[7A", end="")
                self.p("  ╔" + "═" * W + "╗", "accent")
                for r in grid:
                    self.p("  ║" + "".join(r) + "║", "text")
                self.p("  ╚" + "≈" * W + "╝", "accent")
                if runtime.INTERACTIVE:
                    time.sleep(0.12)
        except KeyboardInterrupt:
            pass

    def cmd_clock(self, args=None):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        colon = ["   ", " ▆ ", "   ", " ▆ ", "   "]
        rows = ["", "", "", "", ""]
        for ch in now:
            glyph = colon if ch == ":" else self._FONT.get(ch, self._FONT[" "])
            for r in range(5):
                rows[r] += glyph[r]
        for r in rows:
            self.p(r, "accent")
        self.p(f"  {datetime.date.today().strftime('%A, %d %B %Y')}", "dim")

    SAVER_H = 22

    SAVER_W = 72

    def _screen_dims(self):
        """Best estimate of the drawable area (cols, rows). Uses the size the
        GUI reports; falls back to the console size."""
        if self.term_size:
            W, H = self.term_size
        else:
            try:
                sz = shutil.get_terminal_size((self.SAVER_W, self.SAVER_H + 2))
                W, H = sz.columns, sz.lines
            except Exception:
                W, H = self.SAVER_W, self.SAVER_H + 2
        W = max(24, min(int(W) - 1, 220))
        H = max(8, min(int(H) - 1, 64))
        return W, H

    def cmd_screensaver(self, args=None):
        names = ["matrix", "starfield", "life", "bounce", "fireworks", "fire"]
        if args and args[0].lower() in ("list", "ls"):
            self.p("  screensavers: " + ", ".join(names), "accent")
            self.p("  run: screensaver <name>   (or just 'screensaver' for a random one)", "dim")
            return
        a0 = args[0].lower() if args else ""
        name = a0 if a0 in names else ("starfield" if a0 == "rain" else random.choice(names))
        if self._gui_saver is not None:        # GUI: open a dedicated fullscreen window
            self.p(f"  ░ {name} screensaver — opening in its own window (any key to close) ░", "dim")
            self._gui_saver(name)
            return
        # console fallback: ANSI animation until Ctrl-C
        self.p(f"  ░ screensaver: {name} ░   Ctrl-C to wake", "dim")
        if runtime.INTERACTIVE:
            time.sleep(0.6)
        self._run_screensaver(getattr(self, "_saver_" + name))

    def _run_screensaver(self, render, fps=18):
        """Console screensaver loop (the GUI uses its own window). Renders the
        animation as ANSI until Ctrl-C. `render(state, W, H)` returns
        (chars, colors): two H x W grids (color is an (r,g,b) tuple or None)."""
        self._interrupt = False
        self._screensaver = True
        state, prev_dims, first = {}, None, True
        delay = 1.0 / fps
        try:
            sys.stdout.write("\033[2J\033[H")
            while not self._interrupt:
                W, H = self._screen_dims()
                if (W, H) != prev_dims:           # window resized -> reset & clear
                    state, first, prev_dims = {}, True, (W, H)
                    cells = W * H                 # bigger grids run a touch slower
                    fps = 20 if cells < 3500 else 14 if cells < 7000 else 9
                    delay = 1.0 / fps
                    sys.stdout.write("\033[2J\033[H")
                chars, colors = render(state, W, H)
                out = [] if first else [f"\033[{H}A"]
                first = False
                for y in range(H):
                    out.append(self._ansi_row(chars[y], colors[y], W) + RESET + "\n")
                sys.stdout.write("".join(out))
                try:
                    sys.stdout.flush()
                except Exception:
                    pass
                if not runtime.INTERACTIVE:               # headless: render one frame only
                    break
                time.sleep(delay)
        except KeyboardInterrupt:
            pass
        finally:
            self._screensaver = False
            self._interrupt = False
        sys.stdout.write("\033[2J\033[H")
        self.p("  ...screensaver off.", "dim")

    @staticmethod
    def _ansi_row(chars, colors, W):
        """Turn a row of chars + per-cell colors into one string, emitting a
        color escape ONLY when the color changes. This collapses a row into a
        few segments instead of one per cell — the difference between smooth and
        unwatchable when the window is large. Colors are quantized to 16 steps,
        which also merges near-identical neighbors and bounds the GUI tag count."""
        out = []
        ap = out.append
        last = None
        for x in range(W):
            col = colors[x]
            if col is None:
                if last is not None:
                    ap(RESET); last = None
                ap(" ")
            else:
                q = (col[0] & 0xF0, col[1] & 0xF0, col[2] & 0xF0)
                if q != last:
                    ap(rgb(*q)); last = q
                ap(chars[x])
        return "".join(out)

    def _saver_matrix(self, st, W, H):
        if "drops" not in st:
            st["drops"] = [random.randint(-H, 0) for _ in range(W)]
            st["chars"] = "01ｱｲｳｴｵｶｷｸ#$%&*+=<>"
        rows = [[" "] * W for _ in range(H)]
        color = [[None] * W for _ in range(H)]
        pick = st["chars"]
        for c in range(W):
            head = st["drops"][c]
            for t in range(12):                  # trail length
                y = head - t
                if 0 <= y < H:
                    rows[y][c] = random.choice(pick)
                    if t == 0:
                        color[y][c] = (200, 255, 200)        # bright head
                    else:
                        g = max(40, 255 - t * 22)
                        color[y][c] = (0, g, max(20, g // 3))
            st["drops"][c] += 1
            if st["drops"][c] - 12 > H and random.random() < 0.12:
                st["drops"][c] = random.randint(-6, 0)
        return rows, color

    def _saver_starfield(self, st, W, H):
        cx, cy = W / 2, H / 2
        if "stars" not in st:
            st["stars"] = [[random.uniform(-1, 1), random.uniform(-1, 1)]
                           for _ in range(max(50, W * H // 70))]
        grid = [[" "] * W for _ in range(H)]
        col = [[None] * W for _ in range(H)]
        glyphs = ".·+*o#@"
        for s in st["stars"]:
            s[0] *= 1.06; s[1] *= 1.06          # move outward
            x = int(cx + s[0] * cx)
            y = int(cy + s[1] * cy)
            if not (0 <= x < W and 0 <= y < H):
                s[0], s[1] = random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)
                continue
            depth = min(len(glyphs) - 1, int((abs(s[0]) + abs(s[1])) * len(glyphs)))
            grid[y][x] = glyphs[depth]
            v = 120 + depth * 20
            col[y][x] = (v, v, 255)
        return grid, col

    def _saver_life(self, st, W, H):
        if "grid" not in st or st.get("age", 0) > 300:
            st["grid"] = [[random.random() < 0.28 for _ in range(W)] for _ in range(H)]
            st["age"] = 0
        g = st["grid"]
        new = [[False] * W for _ in range(H)]
        live = 0
        for y in range(H):
            gy0, gy1, gy2 = g[(y - 1) % H], g[y], g[(y + 1) % H]
            row = new[y]
            for x in range(W):
                xm, xp = (x - 1) % W, (x + 1) % W
                n = (gy0[xm] + gy0[x] + gy0[xp] + gy1[xm] + gy1[xp]
                     + gy2[xm] + gy2[x] + gy2[xp])
                if n == 3 or (gy1[x] and n == 2):
                    row[x] = True; live += 1
        st["grid"] = new
        st["age"] = st.get("age", 0) + 1
        if live < 8:
            st["age"] = 999                       # nearly dead -> reseed next frame
        glow = (112, 240, 160)
        chars = [["█" if new[y][x] else " " for x in range(W)] for y in range(H)]
        colors = [[glow if new[y][x] else None for x in range(W)] for y in range(H)]
        return chars, colors

    def _saver_bounce(self, st, W, H):
        word = "PHOSPHOR-OS"
        if "x" not in st:
            st.update(x=random.randint(0, max(0, W - len(word))), y=random.randint(0, H - 1),
                      dx=random.choice([-1, 1]), dy=random.choice([-1, 1]),
                      color=(random.randint(120, 255), random.randint(120, 255),
                             random.randint(120, 255)))
        st["x"] += st["dx"]; st["y"] += st["dy"]
        bounced = False
        if st["x"] <= 0 or st["x"] >= W - len(word):
            st["dx"] *= -1; st["x"] = max(0, min(W - len(word), st["x"])); bounced = True
        if st["y"] <= 0 or st["y"] >= H - 1:
            st["dy"] *= -1; st["y"] = max(0, min(H - 1, st["y"])); bounced = True
        if bounced:
            st["color"] = (random.randint(120, 255), random.randint(120, 255),
                           random.randint(120, 255))
        chars = [[" "] * W for _ in range(H)]
        colors = [[None] * W for _ in range(H)]
        y = st["y"]; col = st["color"]
        for i, ch in enumerate(word):
            x = st["x"] + i
            if 0 <= x < W:
                chars[y][x] = ch; colors[y][x] = col
        return chars, colors

    def _saver_fireworks(self, st, W, H):
        if "rockets" not in st:
            st["rockets"], st["sparks"] = [], []
        if random.random() < 0.16 and len(st["rockets"]) < 4:
            st["rockets"].append({"x": random.randint(6, max(7, W - 6)), "y": H - 1,
                                  "top": random.randint(2, max(3, H // 2))})
        for r in list(st["rockets"]):
            r["y"] -= 1
            if r["y"] <= r["top"]:
                c = (random.randint(120, 255), random.randint(120, 255), random.randint(120, 255))
                for _ in range(26):
                    sp = random.uniform(0.4, 1.7)
                    st["sparks"].append({"x": float(r["x"]), "y": float(r["y"]),
                                         "vx": sp * 1.7 * (random.random() - 0.5) * 2,
                                         "vy": sp * (random.random() - 0.5) * 2,
                                         "life": random.randint(6, 15), "c": c})
                st["rockets"].remove(r)
        for s in list(st["sparks"]):
            s["x"] += s["vx"]; s["y"] += s["vy"]; s["vy"] += 0.15; s["life"] -= 1
            if s["life"] <= 0 or not (0 <= s["x"] < W and 0 <= s["y"] < H):
                st["sparks"].remove(s)
        grid = [[" "] * W for _ in range(H)]
        col = [[None] * W for _ in range(H)]
        for r in st["rockets"]:
            if 0 <= r["y"] < H:
                grid[r["y"]][r["x"]] = "|"; col[r["y"]][r["x"]] = (255, 240, 180)
        for s in st["sparks"]:
            x, y = int(s["x"]), int(s["y"])
            grid[y][x] = random.choice("*+.")
            col[y][x] = s["c"]
        return grid, col

    def _saver_fire(self, st, W, H):
        if "heat" not in st:
            st["heat"] = [[0] * W for _ in range(H)]
        heat = st["heat"]
        bottom = heat[H - 1]
        for x in range(W):                        # seed the bottom row
            bottom[x] = random.randint(180, 255) if random.random() < 0.85 else 0
        for y in range(H - 1):                     # propagate upward, cooling
            row, below = heat[y], heat[y + 1]
            for x in range(W):
                row[x] = max(0, below[(x + random.randint(-1, 1)) % W] - random.randint(12, 38))
        palette = " ...:::+++***###"
        plen = len(palette)
        chars = [[" "] * W for _ in range(H)]
        colors = [[None] * W for _ in range(H)]
        for y in range(H):
            hr = heat[y]; crow = chars[y]; colrow = colors[y]
            for x in range(W):
                h = hr[x]
                if h >= 20:
                    crow[x] = palette[min(plen - 1, h * plen // 256)]
                    colrow[x] = (255, h if h < 255 else 255, h - 160 if h > 160 else 0)
        return chars, colors