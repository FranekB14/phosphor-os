"""Static data: window flag, ANSI codes, themes, ramps, entity art."""

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

__all__ = [
    'WINDOW_FLAG',
    'RESET',
    'BOLD',
    'DIM',
    'THEMES',
    '_ANSI_RE',
    '_VAR_RE',
    '_ENTITY',
    '_EYE_FRAMES',
    '_EYE_TEXT',
    '_EYE_COLOR',
    'ASCII_RAMP',
]

WINDOW_FLAG = "PHOSPHOR_WINDOW"

RESET = "\033[0m"

BOLD = "\033[1m"

DIM = "\033[2m"

THEMES = {
    "phosphor": {"text": (80, 255, 120), "accent": (180, 255, 180),
                 "dim": (40, 130, 60), "warn": (255, 210, 90), "err": (255, 80, 80)},
    "amber":    {"text": (255, 176, 0),  "accent": (255, 215, 120),
                 "dim": (150, 100, 0),  "warn": (255, 230, 150), "err": (255, 90, 60)},
    "ice":      {"text": (90, 210, 255), "accent": (190, 240, 255),
                 "dim": (50, 110, 150), "warn": (255, 220, 120), "err": (255, 90, 110)},
    "blood":    {"text": (255, 70, 70),  "accent": (255, 160, 160),
                 "dim": (150, 30, 30),  "warn": (255, 200, 90), "err": (255, 255, 80)},
    "plasma":   {"text": (220, 110, 255), "accent": (240, 190, 255),
                 "dim": (120, 50, 160), "warn": (255, 220, 120), "err": (255, 90, 90)},
    "mono":     {"text": (225, 225, 225), "accent": (255, 255, 255),
                 "dim": (120, 120, 120), "warn": (255, 230, 150), "err": (255, 110, 110)},
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*(?:\x07|\x1b\\)")

_VAR_RE = re.compile(r"\$\{(\w+)\}|\$(\w+)")

_ENTITY = {
    1: ["     ▟███▙     ", "     ▐███▌     ", "      ▀▀▀      ",
        "      ╱▔╲      ", "     ╱░░░╲     ", "    ╱░###░╲    ",
        "   ╱▒▓▓▓▓▒╲   ", "  ╱▒▓█▌▐█▓▒╲  ", " ╱___________╲ "],
    2: ["      ▟███▙     ", "      ▐███▌     ", "       ▀▀▀      ",
        "  ◣   ╱▔╲   ◢  ", "   ╲ ╱░░░╲ ╱   ", "    ╳░###░╳    ",
        "   ╱▒▓▓▓▓▒╲   ", "  ╱█▼█▼█▼█▼█╲  ", " ╱_____|_____╲ "],
    3: ["      ▟███▙      ", "      ▐███▌      ", "   ◣   ▀▀▀   ◢   ",
        "    ╲ ╱▔▔╲ ╱    ", "    ╳╱░░░░╲╳    ", "    ◖░###░◗    ",
        "   ╱▒▓██▓▒╲   ", "  ╱█▲█▲█▲█▲█╲  ", " ╱____|═|____╲ ",
        "   ╱╱     ╲╲   "],
    4: [" ψ    ▟███▙    ψ ", "  ◣╲  ▐███▌  ╱◢  ", "   ╲╲  ▀▀▀  ╱╱   ",
        "   ╳ ╱▔╳▔╲ ╳   ", "    ╲░◢###◣░╱    ", "   ╱▓⚡▓▓⚡▓╲   ",
        "  ╱█▲▼█▲▼█▲█╲  ", " ╱_|_|_|_|_|_╲ ", "  ╱╱  ╲╳╱  ╲╲  ",
        " ╱╱    ╳    ╲╲ "],
    5: [")ψ▟███▙ψ(", "(▐███▌) ", "◣╲ ▀▀▀ ╱◢", "╳╱◉╲╳╱◉╲╳",
        "░◢◣###◢◣░", "▓⚡██⚡██▓", "█▼▲▼▲▼▲█", "╲WWWWWWW╱",
        "╳▓║╳║▓╳", "║▓║║▓║"],
}

_EYE_FRAMES = {
    1: ["(-)", "(_)", "(-)"],            # drowsy, half-aware
    2: ["(o)", "(O)", "(o)"],            # waking
    3: ["(◉)", "(◎)", "(◉)"],            # fixed on you
    4: ["{◉}", "{◬}", "{◉}"],            # agitated
    5: ["◣◉◢", "▓◬▓", "◤◉◥"],            # unbound
}

_EYE_TEXT = {
    1: ["something shifts behind the static..."],
    2: ["it opens. it has noticed you.",
        "do not look directly into the angle."],
    3: ["the geometry is wrong. it was always wrong.",
        "it is counting your heartbeats."],
    4: ["IT KNOWS THE SHAPE OF YOUR NAME.",
        "THE WALLS ARE ONLY SUGGESTIONS NOW."],
    5: ["△  ALL EYES  △  ALL ANGLES  △  NO EXIT  △",
        "y o u   w e r e   n e v e r   a l o n e",
        "▓▒░ THE ANGLE IS OPEN ░▒▓"],
}

_EYE_COLOR = {1: (120, 200, 255), 2: (255, 210, 90), 3: (255, 140, 40),
              4: (255, 60, 60), 5: (200, 80, 255)}

ASCII_RAMP = "@%#WM8B&$*oahkbdpqwmzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

ASCII_RAMP = "@#W$9876543210?!abc;:+=-,._ "  # shorter, cleaner gradient
