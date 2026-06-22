"""Command-line entry point: picks GUI, console, or eye-window mode."""

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
from .shell import Phosphor, main
from .gui import launch_gui, run_eye_gui


def main_entry():
    use_console = ("--console" in sys.argv) or ("--here" in sys.argv)

    # Easter-egg window mode: `--eyes N` shows the entity, then exits.
    if "--eyes" in sys.argv:
        try:
            lvl = int(sys.argv[sys.argv.index("--eyes") + 1])
        except (ValueError, IndexError):
            lvl = 1
        if gui_available() and not use_console:
            run_eye_gui(lvl)
        else:
            set_console_title("◭  IT  SEES  ◭")
            if os.name == "nt":
                os.system("")
            shrink_and_scatter_window()
            run_cosmic_eye(lvl)
        sys.exit(0)

    # Default experience: the GUI terminal window.
    if gui_available() and not use_console:
        try:
            launch_gui()
            sys.exit(0)
        except Exception as e:
            print(f"GUI could not start ({e}); falling back to console.\n")

    # Console mode (explicit --console/--here, no display, or GUI failed).
    if not use_console and relaunch_in_new_window():
        sys.exit(0)                       # console: open its own window
    set_console_title("PHOSPHOR-OS")
    in_own_window = os.environ.get(WINDOW_FLAG) == "1"
    try:
        main()
    except KeyboardInterrupt:
        print("\n[interrupted]")
    except Exception:
        import traceback
        traceback.print_exc()
        if in_own_window:
            try:
                input("\n[phosphor-os crashed] press Enter to close this window...")
            except Exception:
                pass
