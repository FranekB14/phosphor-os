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

    def cmd_screensaver(self, args=None):
        saver = random.choice(["matrix", "fire", "aquarium"])
        self.p(f"  screensaver: {saver}  (Ctrl-C to wake)", "dim")
        if runtime.INTERACTIVE:
            time.sleep(0.6)
        getattr(self, "cmd_" + saver)()
