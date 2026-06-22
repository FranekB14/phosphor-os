"""ToolsMixin: the `tools` command group."""

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


class ToolsMixin:
    def cmd_python(self, args=None):
        import code
        self.p("  Entering Python. Type exit() or Ctrl-D to return to PHOSPHOR-OS.", "accent")
        self.p("  Tip: the running OS is available as the variable `os_sim`.", "dim")
        banner = self.c(f"  Python {platform.python_version()} on PHOSPHOR-OS", "dim")
        ns = {"os_sim": self, "__name__": "__phosphor__"}
        try:
            code.InteractiveConsole(locals=ns).interact(banner=banner, exitmsg="  ...returning to shell.")
        except SystemExit:
            pass

    def cmd_img2ascii(self, args):
        if not args:
            self.p("usage: img2ascii <path> [width] [--color] [--invert] [--save <virtfile>]", "warn")
            self.p("  example: img2ascii ~/pic.jpg 100 --color --save art.txt", "dim")
            return
        path = os.path.expanduser(args[0])
        width = 80
        use_color = "--color" in args
        invert = "--invert" in args
        save_to = None
        rest = args[1:]
        for i, a in enumerate(rest):
            if a.isdigit():
                width = int(a)
            if a == "--save" and i + 1 < len(rest):
                save_to = rest[i + 1]
        art, err = image_to_ascii(path, width=width, use_color=use_color, invert=invert)
        if err:
            self.p("  " + err, "err"); return
        print(art)
        if save_to:
            # strip ANSI before saving to the virtual file
            import re
            clean = re.sub(r"\033\[[0-9;]*m", "", art)
            self._write_file(save_to, clean + "\n", append=False)
            self.p(f"  saved ASCII art -> {save_to}", "accent")

    def cmd_calc(self, args):
        if not args:
            self.p("usage: calc <expression>", "warn"); return
        expr = " ".join(args)
        import math
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed.update({"abs": abs, "round": round, "min": min, "max": max, "pow": pow})
        try:
            result = eval(expr, {"__builtins__": {}}, allowed)  # sandboxed namespace
            self.p(f"  = {result}", "accent")
        except Exception as e:
            self.p(f"  math error: {e}", "err")

    _FONT = {
        "A": ["  ▄█▄  ", " █   █ ", " █████ ", " █   █ ", " █   █ "],
        "B": [" ████  ", " █   █ ", " ████  ", " █   █ ", " ████  "],
        "C": ["  ███  ", " █     ", " █     ", " █     ", "  ███  "],
        "D": [" ████  ", " █   █ ", " █   █ ", " █   █ ", " ████  "],
        "E": [" █████ ", " █     ", " ███   ", " █     ", " █████ "],
        "F": [" █████ ", " █     ", " ███   ", " █     ", " █     "],
        "G": ["  ███  ", " █     ", " █  ██ ", " █   █ ", "  ███  "],
        "H": [" █   █ ", " █   █ ", " █████ ", " █   █ ", " █   █ "],
        "I": [" █████ ", "   █   ", "   █   ", "   █   ", " █████ "],
        "J": [" █████ ", "    █  ", "    █  ", " █  █  ", "  ██   "],
        "K": [" █   █ ", " █  █  ", " ███   ", " █  █  ", " █   █ "],
        "L": [" █     ", " █     ", " █     ", " █     ", " █████ "],
        "M": [" █   █ ", " ██ ██ ", " █ █ █ ", " █   █ ", " █   █ "],
        "N": [" █   █ ", " ██  █ ", " █ █ █ ", " █  ██ ", " █   █ "],
        "O": ["  ███  ", " █   █ ", " █   █ ", " █   █ ", "  ███  "],
        "P": [" ████  ", " █   █ ", " ████  ", " █     ", " █     "],
        "Q": ["  ███  ", " █   █ ", " █ █ █ ", " █  ██ ", "  ████ "],
        "R": [" ████  ", " █   █ ", " ████  ", " █  █  ", " █   █ "],
        "S": ["  ████ ", " █     ", "  ███  ", "     █ ", " ████  "],
        "T": [" █████ ", "   █   ", "   █   ", "   █   ", "   █   "],
        "U": [" █   █ ", " █   █ ", " █   █ ", " █   █ ", "  ███  "],
        "V": [" █   █ ", " █   █ ", " █   █ ", "  █ █  ", "   █   "],
        "W": [" █   █ ", " █   █ ", " █ █ █ ", " ██ ██ ", " █   █ "],
        "X": [" █   █ ", "  █ █  ", "   █   ", "  █ █  ", " █   █ "],
        "Y": [" █   █ ", "  █ █  ", "   █   ", "   █   ", "   █   "],
        "Z": [" █████ ", "    █  ", "   █   ", "  █    ", " █████ "],
        "0": ["  ███  ", " █  ██ ", " █ █ █ ", " ██  █ ", "  ███  "],
        "1": ["   █   ", "  ██   ", "   █   ", "   █   ", " █████ "],
        "2": ["  ███  ", " █   █ ", "   ██  ", "  █    ", " █████ "],
        "3": [" ████  ", "     █ ", "  ███  ", "     █ ", " ████  "],
        "4": [" █  █  ", " █  █  ", " █████ ", "    █  ", "    █  "],
        "5": [" █████ ", " █     ", " ████  ", "     █ ", " ████  "],
        "6": ["  ███  ", " █     ", " ████  ", " █   █ ", "  ███  "],
        "7": [" █████ ", "    █  ", "   █   ", "  █    ", "  █    "],
        "8": ["  ███  ", " █   █ ", "  ███  ", " █   █ ", "  ███  "],
        "9": ["  ███  ", " █   █ ", "  ████ ", "     █ ", "  ███  "],
        " ": ["   ", "   ", "   ", "   ", "   "],
        "!": ["  █  ", "  █  ", "  █  ", "     ", "  █  "],
        "?": ["  ███  ", " █   █ ", "   ██  ", "       ", "   █   "],
        ".": ["   ", "   ", "   ", "   ", " █ "],
        "-": ["     ", "     ", " ███ ", "     ", "     "],
    }

    def cmd_banner(self, args):
        if not args:
            self.p("usage: banner <text>", "warn"); return
        text = " ".join(args).upper()
        rows = ["", "", "", "", ""]
        for ch in text:
            glyph = self._FONT.get(ch, self._FONT["?"])
            for r in range(5):
                rows[r] += glyph[r]
        for r in rows:
            self.p(r, "accent")

    def cmd_echo(self, args):
        self.p("  " + " ".join(args), "text")

    def cmd_rev(self, args):
        if not args and self._pipe_in is not None:
            for line in self._pipe_in.splitlines():
                self.p(line[::-1], "text")
            return
        self.p("  " + " ".join(args)[::-1], "text")

    def cmd_upper(self, args):
        if not args and self._pipe_in is not None:
            for line in self._pipe_in.splitlines():
                self.p(line.upper(), "text")
            return
        self.p("  " + " ".join(args).upper(), "text")

    def cmd_lower(self, args):
        if not args and self._pipe_in is not None:
            for line in self._pipe_in.splitlines():
                self.p(line.lower(), "text")
            return
        self.p("  " + " ".join(args).lower(), "text")

    def cmd_roll(self, args):
        spec = args[0] if args else "1d6"
        try:
            n, sides = spec.lower().split("d")
            n, sides = int(n or 1), int(sides)
            if not (1 <= n <= 100 and 2 <= sides <= 1000):
                raise ValueError
        except Exception:
            self.p("usage: roll NdM   (e.g. roll 2d20)", "warn"); return
        rolls = [random.randint(1, sides) for _ in range(n)]
        self.p(f"  rolled {spec}: {rolls}  total = {sum(rolls)}", "accent")

    def cmd_flip(self, args=None):
        self.p("  " + random.choice(["HEADS", "TAILS"]), "accent")

    _MORSE = {
        "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
        "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
        "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
        "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
        "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
        "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
        "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..",
        "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...",
        ":": "---...", "'": ".----.", "=": "-...-", "+": ".-.-.", "-": "-....-",
        "@": ".--.-.",
    }

    def cmd_morse(self, args):
        if not args:
            self.p("usage: morse <text>   or   morse .... .", "warn"); return
        raw = " ".join(args)
        # decode if it looks like morse (only . - / and spaces)
        if set(raw) <= set(". -/"):
            rev = {v: k for k, v in self._MORSE.items()}
            words = raw.strip().split("/")
            out = []
            for w in words:
                letters = [rev.get(code, "?") for code in w.split()]
                out.append("".join(letters))
            self.p("  " + " ".join(out), "accent")
        else:
            parts = []
            for ch in raw.upper():
                if ch == " ":
                    parts.append("/")
                else:
                    parts.append(self._MORSE.get(ch, "?"))
            self.p("  " + " ".join(parts), "accent")

    def cmd_leet(self, args):
        if not args:
            self.p("usage: leet <text>", "warn"); return
        table = str.maketrans({"a": "4", "A": "4", "e": "3", "E": "3",
                               "i": "1", "I": "1", "o": "0", "O": "0",
                               "t": "7", "T": "7", "s": "5", "S": "5",
                               "l": "1", "g": "9", "b": "8"})
        self.p("  " + " ".join(args).translate(table), "accent")

    def cmd_rot13(self, args):
        if not args:
            self.p("usage: rot13 <text>", "warn"); return
        import codecs
        self.p("  " + codecs.encode(" ".join(args), "rot_13"), "accent")

    def cmd_bases(self, args):
        if not args:
            self.p("usage: bases <number>   (accepts 0x.. 0b.. too)", "warn"); return
        try:
            n = int(args[0], 0)
        except ValueError:
            self.p("  not an integer.", "err"); return
        self.p(f"  DEC  {n}", "text")
        self.p(f"  BIN  {bin(n)}", "text")
        self.p(f"  OCT  {oct(n)}", "text")
        self.p(f"  HEX  {hex(n).upper().replace('X', 'x')}", "text")

    def cmd_asciitable(self, args=None):
        self.p("  printable ASCII (32-126):", "accent")
        row = []
        for code in range(32, 127):
            row.append(f"{code:>3}:{chr(code)}")
            if len(row) == 8:
                self.p("  " + "  ".join(row), "text")
                row = []
        if row:
            self.p("  " + "  ".join(row), "text")
