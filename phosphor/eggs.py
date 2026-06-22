"""EggsMixin: the `eggs` command group."""

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


class EggsMixin:
    EASTER_EGGS = {
        "bill cypher": "_egg_angle",
        "bill cipher": "_egg_angle",
        "the angle": "_egg_angle",
        "open the angle": "_egg_angle",
        "xyzzy": "_egg_xyzzy",
        "the cake is a lie": "_egg_cake",
        "sudo make me a sandwich": "_egg_sandwich",
        "make me a sandwich": "_egg_sandwich",
        "42": "_egg_42",
        "hello world": "_egg_helloworld",
        "do a barrel roll": "_egg_barrelroll",
    }

    def _egg_angle(self):
        """Flagship egg: the entity 'takes over' -- a glitch takeover plays in
        this window, then a big swarm of tiny scattered windows erupts across
        the screen. Falls back to an inline show if windows can't be opened."""
        self.p("  △ . . . the static thickens . . . △", "err")
        if runtime.INTERACTIVE:
            time.sleep(0.5)
        glitch = "▓▒░#@%&*/\\|<>"
        takeover = [
            "[sys] integrity check ............ FAILED",
            "[sys] unknown process ANGLE.SYS in ring-0",
            "[sys] reality buffer overflow at 0x0EYE",
            "[sys] kernel surrendering control . . .",
        ]
        for line in takeover:
            out = "".join(random.choice(glitch) if (c != " " and random.random() < 0.08) else c
                          for c in line)
            self.p("  " + out, "err")
            if runtime.INTERACTIVE:
                time.sleep(0.35)
        self.p("  ░▒▓  THE ANGLE HAS ASSUMED CONTROL  ▓▒░", "warn")
        self._snd("angle")
        if runtime.INTERACTIVE:
            time.sleep(0.5)
        self.p("  manifesting across the system...", "err")

        # weighted toward higher levels; a swarm for the "takeover" feel
        levels = [random.choice([1, 2, 3, 3, 4, 4, 5, 5, 5]) for _ in range(14)]
        opened = 0
        for lv in levels:
            if runtime.GUI_ACTIVE:
                ok = _spawn_eye_process(lv)             # small borderless GUI window
            else:
                ok = _open_terminal(_build_self_cmd(["--eyes", str(lv)]),
                                    {WINDOW_FLAG: "1"})  # console window
            if ok:
                opened += 1
                if runtime.INTERACTIVE:
                    time.sleep(0.12)            # cascade them in
        if opened:
            self.p(f"  {opened} angles are loose. they are everywhere now.", "err")
            self.p("  (close their windows to banish them)", "dim")
        else:
            for lv in [1, 2, 3, 4, 5]:
                run_cosmic_eye(lv, inline=True)
            self.p("  the angle recedes... for now. you feel watched.", "err")

    def _egg_xyzzy(self):
        self.p("  Nothing happens.", "dim")
        if runtime.INTERACTIVE:
            time.sleep(0.8)
        self.p("  ...or did it?", "accent")

    def _egg_cake(self):
        cake = [
            "    ' ' '    ",
            "   _|_|_|_   ",
            "  (~~~~~~~)  ",
            "  |=======|  ",
            "  |_______|  ",
        ]
        for ln in cake:
            self.p("  " + ln, "accent")
        self.p("  The cake is a lie. But the segfault is real.", "err")

    def _egg_sandwich(self):
        if "sudo" in (self.history[-1].lower() if self.history else ""):
            self.p("  Okay.  [=== a fresh sandwich ===]", "accent")
            self.p("  (you wield root privileges in the kitchen)", "dim")
        else:
            self.p("  What? Make it yourself.", "warn")
            self.p("  (try saying 'sudo' first)", "dim")

    def _egg_42(self):
        self.p("  42", "accent")
        self.p("  The Answer to the Ultimate Question of Life,", "text")
        self.p("  the Universe, and Everything. Now... the Question?", "dim")

    def _egg_helloworld(self):
        self.p('  >>> print("Hello, World!")', "dim")
        self.p("  Hello, World!", "accent")
        self.p("  Welcome aboard, operator.", "text")

    def _egg_barrelroll(self):
        spinner = ["—", "\\", "|", "/"]
        if runtime.INTERACTIVE:
            for i in range(16):
                print("\r" + self.c("  rolling... " + spinner[i % 4], "accent"), end="", flush=True)
                time.sleep(0.08)
            print()
        self.p("  ↻ whee! ↺", "warn")
