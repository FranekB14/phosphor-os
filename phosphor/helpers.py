"""Free functions: platform/window glue, ANSI, storage, image, eye art."""

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

__all__ = [
    '_is_frozen',
    'set_console_title',
    'shrink_and_scatter_window',
    '_build_self_cmd',
    '_open_terminal',
    'relaunch_in_new_window',
    'strip_ansi',
    'rgb',
    'run_cosmic_eye',
    '_new_dir',
    '_new_file',
    'app_data_dir',
    '_default_disk',
    'image_to_ascii',
    'gui_available',
    '_spawn_eye_process',
]


def _is_frozen():
    """True when running as a PyInstaller-built .exe."""
    return getattr(sys, "frozen", False)


def set_console_title(title="PHOSPHOR-OS"):
    """Name the terminal window, so the new window reads 'PHOSPHOR-OS'."""
    try:
        if os.name == "nt":
            os.system(f"title {title}")
        else:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
    except Exception:
        pass


def shrink_and_scatter_window(cols=20, lines=13):
    """Resize this console to a small square and fling it to a random spot on
    screen. Used by the easter-egg windows. Windows uses the Win32 API for the
    move; other platforms get a best-effort resize escape (position varies)."""
    try:
        if os.name == "nt":
            os.system(f"mode con: cols={cols} lines={lines}")
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            u = ctypes.windll.user32
            hwnd = k.GetConsoleWindow()
            if hwnd:
                sw = u.GetSystemMetrics(0)              # screen width
                sh = u.GetSystemMetrics(1)              # screen height
                rect = wintypes.RECT()
                u.GetWindowRect(hwnd, ctypes.byref(rect))
                ww = max(1, rect.right - rect.left)
                wh = max(1, rect.bottom - rect.top)
                x = random.randint(0, max(0, sw - ww))
                y = random.randint(0, max(0, sh - wh))
                SWP_NOSIZE, SWP_NOZORDER = 0x0001, 0x0004
                u.SetWindowPos(hwnd, 0, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER)
        else:
            sys.stdout.write(f"\033[8;{lines};{cols}t")   # xterm resize (rows;cols)
            sys.stdout.flush()
    except Exception:
        pass


def _build_self_cmd(extra=None):
    """The command that launches THIS program again (script or frozen .exe)."""
    if _is_frozen():
        base = [sys.executable]                                # the .exe itself
    else:
        base = [sys.executable, os.path.abspath(sys.argv[0])]  # python script.py
    return base + list(extra or [])


def _open_terminal(cmd, env_extra=None):
    """Open `cmd` in a brand-new terminal window. Returns True on success,
    False if no separate terminal could be opened (caller decides fallback)."""
    env_extra = env_extra or {}
    try:
        if os.name == "nt":
            env = dict(os.environ, **env_extra)
            CREATE_NEW_CONSOLE = 0x00000010
            subprocess.Popen(cmd, creationflags=CREATE_NEW_CONSOLE,
                             env=env, close_fds=True)
            return True

        # Unix-likes: bake env vars into the shell string (a fresh shell starts).
        prefix = "".join(f"{k}={v} " for k, v in env_extra.items())
        inner = prefix + " ".join(shlex.quote(c) for c in cmd)

        if sys.platform == "darwin":
            script = f'tell application "Terminal" to do script "{inner}"'
            subprocess.Popen(["osascript",
                              "-e", 'tell application "Terminal" to activate',
                              "-e", script])
            return True

        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return False                  # headless -> caller runs inline
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole",
                     "xfce4-terminal", "kitty", "alacritty", "xterm"):
            if shutil.which(term):
                subprocess.Popen([term, "-e", "bash", "-c", inner])
                return True
        return False
    except Exception:
        return False


def relaunch_in_new_window():
    """
    Spawn this program in its own terminal window and return True (the caller
    should then exit). Returns False if we should just run inline -- because we
    already are the spawned window, the user passed --here, or no separate
    terminal could be opened (we degrade gracefully instead of failing).
    """
    if os.environ.get(WINDOW_FLAG) == "1":
        return False                      # already inside our own window
    if "--here" in sys.argv:
        return False                      # user wants the current terminal
    passthrough = [a for a in sys.argv[1:] if a != "--here"]
    return _open_terminal(_build_self_cmd(passthrough), {WINDOW_FLAG: "1"})


def strip_ansi(text):
    return _ANSI_RE.sub("", text)


def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def run_cosmic_eye(level, inline=False):
    """Animate the entity at a given intensity. Used by `--eyes N` windows
    and as the inline fallback when no windows can be opened."""
    level = max(1, min(5, level))
    base = _EYE_COLOR[level]
    eyes = _EYE_FRAMES[level]
    texts = _EYE_TEXT[level]
    glitch = "▓▒░#@%&*/\\|<>≈∴×"
    if runtime.INTERACTIVE:
        frames = 130 if not inline else level * 6
    else:
        frames = 2                              # piped/non-tty: just a peek

    def colorize(intensity):
        # higher level + flicker pushes the hue toward red/violet
        r, g, b = base
        if level >= 4 and random.random() < 0.3:
            return rgb(255, random.randint(0, 60), random.randint(0, 80))
        return rgb(r, g, b)

    try:
        for fi in range(frames):
            eye = eyes[fi % len(eyes)]
            rows = [ln.replace("###", eye).center(18) for ln in _ENTITY[level]]
            painted = []
            for ln in rows:
                chars = list(ln)
                for i, ch in enumerate(chars):
                    if ch != " " and random.random() < 0.025 * level:
                        chars[i] = random.choice(glitch)
                painted.append("".join(chars))
            if runtime.INTERACTIVE:
                print("\033[H\033[J", end="")    # clear & home
            jitter = " " * random.randint(0, 1 if level >= 3 else 0)
            col = colorize(fi)
            print(col, end="")
            for ln in painted:
                print(jitter + ln)
            print()
            line = random.choice(texts)
            if level >= 4:                       # corrupt the words at high levels
                line = "".join(random.choice(glitch) if (c != " " and random.random() < 0.12) else c
                               for c in line)
            print(jitter + " " + line[:23])
            print(RESET, end="", flush=True)
            if runtime.INTERACTIVE:
                time.sleep(max(0.05, 0.16 - level * 0.018))
    except KeyboardInterrupt:
        pass
    print(RESET, end="")
    if runtime.INTERACTIVE and not inline:
        print(rgb(*base) + "\n  ...the angle closes. for now." + RESET)
        time.sleep(0.6)


def _new_dir():
    return {"type": "dir", "children": {}}


def _new_file(content=""):
    return {"type": "file", "content": content,
            "modified": datetime.datetime.now().isoformat(timespec="seconds")}


def app_data_dir():
    """
    A stable, writable folder for the saved disk -- so persistence works no
    matter where the script or .exe is launched from. (Saving next to an .exe
    installed in Program Files would fail on permissions; this avoids that.)
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "PhosphorOS")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
        path = os.path.join(base, "phosphor-os")
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        return os.getcwd()   # fall back to current dir if that fails


def _default_disk():
    """A fresh disk image with a small starter filesystem."""
    root = _new_dir()
    home = _new_dir()
    docs = _new_dir()
    docs["children"]["welcome.txt"] = _new_file(
        "Welcome to PHOSPHOR-OS.\n"
        "This is a virtual file living in a simulated disk.\n"
        "Try:  cat welcome.txt   |   tree /   |   help\n"
    )
    home["children"]["docs"] = docs
    home["children"]["readme.md"] = _new_file(
        "# PHOSPHOR-OS\n"
        "Type `help` for commands.\n"
        "Highlights: `python`, `img2ascii`, `matrix`, `theme`.\n"
    )
    root["children"]["home"] = home
    root["children"]["sys"] = _new_dir()
    root["children"]["sys"]["children"]["version"] = _new_file("PHOSPHOR-OS v2.3\n")
    return root


def image_to_ascii(path, width=80, use_color=False, invert=False):
    """Convert an image file on the *real* disk into ASCII art text."""
    try:
        from PIL import Image
    except ImportError:
        return None, ("Pillow is not installed. Run:  pip install Pillow")

    if not os.path.isfile(path):
        return None, f"No such image file on host disk: {path}"

    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        return None, f"Could not open image: {e}"

    w, h = img.size
    # Characters are ~2x taller than wide -> scale height by 0.5.
    aspect = h / w
    new_w = max(1, int(width))
    new_h = max(1, int(aspect * new_w * 0.5))
    img = img.resize((new_w, new_h))
    pixels = img.load()

    ramp = ASCII_RAMP[::-1] if invert else ASCII_RAMP
    n = len(ramp) - 1

    lines = []
    for y in range(new_h):
        row = []
        for x in range(new_w):
            r, g, b = pixels[x, y]
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b   # perceptual luminance
            ch = ramp[int(lum / 255 * n)]
            if use_color:
                row.append(f"{rgb(r, g, b)}{ch}")
            else:
                row.append(ch)
        lines.append("".join(row) + (RESET if use_color else ""))
    return "\n".join(lines), None


def gui_available():
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


def _spawn_eye_process(level):
    """Launch a separate process that opens a small borderless eye window."""
    cmd = _build_self_cmd(["--eyes", str(level)])
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000      # CREATE_NO_WINDOW (no console)
    try:
        subprocess.Popen(cmd, **kwargs)
        return True
    except Exception:
        return False
