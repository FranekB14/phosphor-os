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
        self.p(f"  Python {platform.python_version()} on PHOSPHOR-OS", "dim")
        self.p("  Type exit() (or an empty line at Ctrl-D) to return to the shell.", "accent")
        self.p("  Tip: the running OS is available as the variable `os_sim`.", "dim")
        ns = {"os_sim": self, "__name__": "__phosphor__"}
        console = code.InteractiveConsole(locals=ns)
        more = False
        while True:
            line = self._input("  ... " if more else "  >>> ", "dim")
            if line is None:                       # EOF / Ctrl-D / cancel
                self.p("  ...returning to shell.", "dim"); return
            if not more and line.strip() in ("exit", "exit()", "quit", "quit()"):
                self.p("  ...returning to shell.", "dim"); return
            # Capture whatever the executed line prints (results, errors, output)
            # so it shows up here instead of going to the real stdout/stderr —
            # those may be the wrong streams (GUI) or None (windowed .exe).
            buf = io.StringIO()
            saved_out, saved_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = buf
            try:
                more = console.push(line)
            except SystemExit:
                sys.stdout, sys.stderr = saved_out, saved_err
                self.p("  ...returning to shell.", "dim"); return
            except Exception as e:
                more = False
                buf.write(f"{type(e).__name__}: {e}\n")
            finally:
                sys.stdout, sys.stderr = saved_out, saved_err
            out = buf.getvalue()
            if out:
                for ln in out.rstrip("\n").split("\n"):
                    self.p(ln, "text")

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

    def cmd_convert(self, args):
        if len(args) < 3:
            self.p("usage: convert <value> <from> <to>   e.g. convert 10 km mi", "warn")
            self.p("  length: km m cm mm mi yd ft in    weight: kg g mg lb oz t", "dim")
            self.p("  temperature: c f k", "dim")
            return
        try:
            value = float(args[0])
        except ValueError:
            self.p("  the first argument must be a number.", "err"); return
        frm, to = args[1].lower(), args[2].lower()
        length = {"km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
                  "mi": 1609.344, "yd": 0.9144, "ft": 0.3048, "in": 0.0254}
        weight = {"t": 1e6, "kg": 1000, "g": 1, "mg": 0.001, "lb": 453.592, "oz": 28.3495}
        if frm in length and to in length:
            result = value * length[frm] / length[to]
        elif frm in weight and to in weight:
            result = value * weight[frm] / weight[to]
        elif frm in ("c", "f", "k") and to in ("c", "f", "k"):
            c = value if frm == "c" else (value - 32) * 5 / 9 if frm == "f" else value - 273.15
            result = c if to == "c" else c * 9 / 5 + 32 if to == "f" else c + 273.15
        else:
            self.p("  can't convert those units (mismatched or unknown).", "err"); return
        self.p(f"  {value:g} {frm} = {result:g} {to}", "accent")

    def cmd_todo(self, args):
        if not args:
            if not self.todos:
                self.p("  (no tasks) — add one with: todo add <text>", "dim"); return
            self.p("  ─ TO-DO ────────────────────────", "accent")
            for i, t in enumerate(self.todos, 1):
                mark = "x" if t.get("done") else " "
                role = "dim" if t.get("done") else "text"
                self.p(f"  {i:>3} [{mark}] {t['text']}", role)
            return
        sub, rest = args[0].lower(), " ".join(args[1:]).strip()
        if sub == "add":
            if not rest:
                self.p("usage: todo add <text>", "warn"); return
            self.todos.append({"text": rest, "done": False}); self.save_config()
            self.p(f"  added: {rest}", "accent")
        elif sub in ("done", "do", "check") and rest.isdigit():
            i = int(rest) - 1
            if 0 <= i < len(self.todos):
                self.todos[i]["done"] = not self.todos[i]["done"]; self.save_config()
                state = "done" if self.todos[i]["done"] else "todo"
                self.p(f"  {state}: {self.todos[i]['text']}", "accent")
            else:
                self.p("  no task with that number.", "err")
        elif sub in ("rm", "del", "remove") and rest.isdigit():
            i = int(rest) - 1
            if 0 <= i < len(self.todos):
                gone = self.todos.pop(i); self.save_config()
                self.p(f"  removed: {gone['text']}", "accent")
            else:
                self.p("  no task with that number.", "err")
        elif sub == "clear":
            self.todos = []; self.save_config()
            self.p("  all tasks cleared.", "accent")
        else:
            self.p("usage: todo | todo add <text> | todo done <n> | todo rm <n> | todo clear", "warn")

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
