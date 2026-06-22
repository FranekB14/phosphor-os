"""SystemMixin: the `system` command group."""

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


class SystemMixin:
    def cmd_help(self, args=None):
        args = args or []
        if args:
            name = args[0].lower()
            entry = self.commands.get(name)
            if not entry:
                self.p(f"No help: unknown command '{name}'.", "err"); return
            primary, group, usage, desc = entry[1]
            aliases = [n for n, (h, m) in self.commands.items()
                       if m[0] == primary and n != primary]
            self.p(f"  {primary}  [{group}]", "accent")
            self.p(f"    usage : {usage}", "text")
            self.p(f"    info  : {desc}", "text")
            if aliases:
                self.p(f"    alias : {', '.join(sorted(aliases))}", "dim")
            return
        self.p("  ╔══════════════════════════════════════════════════════════╗", "dim")
        self.p("  ║  PHOSPHOR-OS COMMAND REFERENCE                            ║", "accent")
        self.p("  ╚══════════════════════════════════════════════════════════╝", "dim")
        groups = {}
        for primary, aliases, group, usage, desc in self.SPEC:
            groups.setdefault(group, []).append((primary, desc))
        order = ["files", "tools", "system", "network", "toys", "games"]
        titles = {"files": "FILESYSTEM", "tools": "TOOLS",
                  "system": "SYSTEM", "network": "NETWORK",
                  "toys": "TOYS", "games": "GAMES"}
        for g in order:
            if not groups.get(g):
                continue
            self.p(f"\n  ── {titles[g]} " + "─" * (46 - len(titles[g])), "accent")
            for primary, desc in groups[g]:
                self.p(f"    {primary:<11} {desc}", "text")
        self.p("\n  Tip: 'help <command>' shows usage + aliases.", "dim")

    def cmd_clear(self, args=None):
        # ANSI clear works in real terminals AND in the GUI emulator.
        print("\033[2J\033[3J\033[H", end="")

    def cmd_theme(self, args=None):
        args = args or []
        if not args:
            self.p("  available themes: " + ", ".join(THEMES), "text")
            self.p(f"  current: {self.theme_name}", "accent")
            self.p("  usage: theme <name>", "dim")
            return
        name = args[0].lower()
        if name not in THEMES:
            self.p(f"Unknown theme '{name}'. Options: {', '.join(THEMES)}", "err"); return
        self.theme_name = name
        self.theme = THEMES[name]
        self.save_config()
        self.p(f"  theme set to {name}.", "accent")

    def cmd_sysinfo(self, args=None):
        up = int(time.time() - self.start_time)
        files = self._count_nodes("file")
        dirs = self._count_nodes("dir")
        art = [
            "      .----------------.   ",
            "     |  ::::::::::::::  |  ",
            "     |  :  PHOSPHOR  :  |  ",
            "     |  :   ~v{ver}~    :  |  ".format(ver=self.VERSION),
            "     |  ::::::::::::::  |  ",
            "      '----------------'   ",
            "       _||________||_      ",
            "      '----------------'   ",
        ]
        info = [
            f"{self.user}@phosphor",
            "-----------------",
            f"OS      : PHOSPHOR-OS v{self.VERSION}",
            f"Host    : {platform.system()} {platform.release()}",
            f"Kernel  : phosphor-kernel 2.3-crt",
            f"Shell   : phosphor-shell",
            f"Theme   : {self.theme_name}",
            f"Uptime  : {up // 60}m {up % 60}s",
            f"Files   : {files}   Dirs: {dirs}",
            f"Python  : {platform.python_version()}",
        ]
        for i in range(max(len(art), len(info))):
            left = art[i] if i < len(art) else " " * 26
            right = info[i] if i < len(info) else ""
            print(self.c(left, "accent") + "  " + self.c(right, "text"))

    def _count_nodes(self, kind):
        total = 0

        def walk(n):
            nonlocal total
            for child in n["children"].values():
                if child["type"] == kind:
                    total += 1
                if child["type"] == "dir":
                    walk(child)
        walk(self.disk)
        return total

    def cmd_history(self, args=None):
        if not self.history:
            self.p("  (no history)", "dim"); return
        for i, h in enumerate(self.history, 1):
            self.p(f"  {i:>4}  {h}", "text")

    def cmd_alias(self, args):
        if not args:
            if not self.aliases:
                self.p("  (no aliases)", "dim"); return
            for name in sorted(self.aliases):
                self.p(f"  {name} = {self.aliases[name]}", "text")
            return
        joined = " ".join(args)
        if "=" not in joined:
            name = args[0]
            if name in self.aliases:
                self.p(f"  {name} = {self.aliases[name]}", "text")
            else:
                self.p(f"  no alias named '{name}'.", "dim")
            return
        name, value = joined.split("=", 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if not name:
            self.p("usage: alias name=\"command\"", "warn"); return
        self.aliases[name] = value
        self.save_config()
        self.p(f"  alias set: {name} = {value}", "accent")

    def cmd_unalias(self, args):
        if not args:
            self.p("usage: unalias <name>", "warn"); return
        if self.aliases.pop(args[0], None) is not None:
            self.save_config()
            self.p(f"  removed alias '{args[0]}'.", "accent")
        else:
            self.p(f"  no alias named '{args[0]}'.", "dim")

    def cmd_set(self, args):
        if not args:
            if not self.env:
                self.p("  (no variables set)", "dim")
            for name in sorted(self.env):
                self.p(f"  {name}={self.env[name]}", "text")
            self.p("  built-ins: $USER $VERSION $CWD $THEME $HOME", "dim")
            return
        joined = " ".join(args)
        if "=" not in joined:
            self.p("usage: set NAME=value", "warn"); return
        name, value = joined.split("=", 1)
        name = name.strip()
        if not name.replace("_", "").isalnum():
            self.p("  variable names must be letters/digits/underscore.", "err"); return
        self.env[name] = value.strip().strip('"').strip("'")
        self.save_config()
        self.p(f"  {name}={self.env[name]}", "accent")

    def cmd_unset(self, args):
        if not args:
            self.p("usage: unset <NAME>", "warn"); return
        if self.env.pop(args[0], None) is not None:
            self.save_config()
            self.p(f"  unset '{args[0]}'.", "accent")
        else:
            self.p(f"  no variable named '{args[0]}'.", "dim")

    def cmd_run(self, args):
        if not args:
            self.p("usage: run <file>", "warn"); return
        node = self._get_node(self._resolve(args[0]))
        if not node or node["type"] != "file":
            self.p(f"No such script: {args[0]}", "err"); return
        self.p(f"  -- running {args[0]} --", "dim")
        self._run_script(node["content"])

    def _version_tuple(self, s):
        nums = re.findall(r"\d+", s or "")
        return tuple(int(n) for n in nums) if nums else (0,)

    def _launcher_dir(self):
        """The folder the launcher (.py or .exe) is sitting in."""
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        try:
            base = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else __file__
        except Exception:
            base = os.getcwd()
        return os.path.dirname(base) or os.getcwd()

    def _updatable_root(self):
        """Folder that holds the replaceable phosphor/ package on real disk,
        or None if the code is frozen *inside* the executable (can't be
        replaced). A launcher .exe with a loose phosphor/ folder beside it is
        updatable; a fully-bundled --onefile exe is not."""
        try:
            import phosphor
            pkg_file = os.path.abspath(phosphor.__file__)
        except Exception:
            return self._launcher_dir()          # single-file build / monolith
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and pkg_file.startswith(os.path.abspath(meipass)):
            return None                          # bundled inside the exe
        return os.path.dirname(os.path.dirname(pkg_file))  # parent of phosphor/

    def _install_dir(self):
        """Folder the running program lives in (where files get replaced)."""
        return self._updatable_root() or self._launcher_dir()

    def _http_get(self, url, timeout=20):
        req = urllib.request.Request(url, headers={"User-Agent": "PHOSPHOR-OS-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def _remote_version(self, repo, branch):
        """Best effort: read a top-level VERSION file from the repo."""
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/VERSION"
        try:
            return self._http_get(url, timeout=12).decode("utf-8", "replace").strip()
        except Exception:
            return None

    def cmd_update(self, args):
        args = list(args)
        check_only = "--check" in args
        force = "--force" in args
        repo, branch = self.update_repo, self.update_branch
        if "--repo" in args:
            i = args.index("--repo")
            if i + 1 < len(args):
                repo = args[i + 1]
                self.update_repo = repo
                self.save_config()
                self.p(f"  update repo set to: {repo}", "accent")
        if "--branch" in args:
            i = args.index("--branch")
            if i + 1 < len(args):
                branch = args[i + 1]
                self.update_branch = branch
                self.save_config()

        if self._updatable_root() is None:
            self.p("  This .exe has all the code bundled inside it, so it can't", "warn")
            self.p("  replace itself. To enable self-update, build it as a launcher", "warn")
            self.p("  with a loose phosphor/ folder beside the .exe (see the build", "warn")
            self.p("  notes), or download the new build manually.", "warn")
            return
        if "/" not in repo or repo.startswith("your-username/"):
            self.p("  No GitHub repo configured yet.", "warn")
            self.p("  Set one with:  update --repo <github-user>/<repo>", "dim")
            return

        self.p(f"  current version : v{self.VERSION}", "text")
        self.p(f"  checking {repo}@{branch} ...", "dim")
        remote = self._remote_version(repo, branch)
        if remote:
            self.p(f"  available version: v{remote}", "text")
            newer = self._version_tuple(remote) > self._version_tuple(self.VERSION)
            if not newer and not force:
                self.p("  Already up to date.  (use --force to reinstall)", "accent")
                return
        else:
            self.p("  (no VERSION file found in repo -- will fetch latest anyway)", "dim")

        if check_only:
            self.p("  --check only: not installing.", "dim")
            return

        if self._is_interactive():
            ans = self._input("  Download and install now? [y/N] ", "warn")
            if not ans or ans.strip().lower() not in ("y", "yes"):
                self.p("  cancelled.", "dim"); return

        url = f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}"
        self.p("  downloading...", "dim")
        try:
            blob = self._http_get(url, timeout=60)
        except urllib.error.HTTPError as e:
            self.p(f"  download failed: HTTP {e.code} "
                   f"({'repo/branch not found' if e.code == 404 else e.reason}).", "err")
            return
        except Exception as e:
            self.p(f"  download failed: {e}", "err")
            self.p("  (check your internet connection and the repo name.)", "dim")
            return

        try:
            self._install_zip(blob)
        except Exception as e:
            self.p(f"  install failed: {e}", "err")
            return

    def _install_zip(self, blob):
        install_dir = self._install_dir()
        with tempfile.TemporaryDirectory() as tmp:
            zf = zipfile.ZipFile(io.BytesIO(blob))
            zf.extractall(tmp)
            entries = [os.path.join(tmp, d) for d in os.listdir(tmp)]
            roots = [d for d in entries if os.path.isdir(d)]
            src_root = roots[0] if roots else tmp     # github wraps in one folder

            # back up current install (the package dir + launcher / monolith)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = os.path.join(install_dir, ".phosphor_backups", stamp)
            os.makedirs(backup, exist_ok=True)
            for item in ("phosphor", "phosphor_os.py"):
                src = os.path.join(install_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(backup, item))
                elif os.path.isfile(src):
                    shutil.copy2(src, os.path.join(backup, item))

            # mirror the repo contents into the install dir
            copied = 0
            for dirpath, dirnames, filenames in os.walk(src_root):
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", ".phosphor_backups", "__pycache__")]
                rel = os.path.relpath(dirpath, src_root)
                dest_dir = install_dir if rel == "." else os.path.join(install_dir, rel)
                os.makedirs(dest_dir, exist_ok=True)
                for fn in filenames:
                    shutil.copy2(os.path.join(dirpath, fn), os.path.join(dest_dir, fn))
                    copied += 1

        self.p(f"  installed {copied} file(s) into {install_dir}", "accent")
        self.p(f"  previous version backed up to .phosphor_backups/{stamp}", "dim")
        self.p("  ✔ update complete — restart PHOSPHOR-OS to run the new version.", "accent")

    def _is_interactive(self):
        return runtime.INTERACTIVE or runtime.GUI_ACTIVE

    def cmd_whoami(self, args=None):
        self.p("  " + self.user, "text")

    def cmd_scores(self, args=None):
        labels = {
            "guess_best": "Guess (fewest tries)",
            "quiz_best": "Quiz (best score)",
            "wordle_best": "Wordle (fewest guesses)",
            "rps_wins": "Rock-Paper-Scissors wins",
            "ttt_wins": "Tic-Tac-Toe wins",
            "hangman_wins": "Hangman wins",
            "2048_best": "2048 (best score)",
            "minesweeper_wins": "Minesweeper wins",
            "blackjack_wins": "Blackjack wins",
        }
        if not self.scores:
            self.p("  no scores yet — go play some games!", "dim"); return
        self.p("  ── HIGH SCORES ─────────────────", "accent")
        for key, label in labels.items():
            if key in self.scores:
                self.p(f"    {label:<28} {self.scores[key]}", "text")

    def cmd_setname(self, args):
        if not args:
            self.p("usage: setname <name>", "warn"); return
        self.user = args[0].strip()[:20].lower()
        self.save_config()
        self.p(f"  you are now '{self.user}'.", "accent")

    def cmd_secrets(self, args=None):
        hints = [
            "Some words are not commands, yet the OS still listens for them.",
            "Adventurers of old muttered a magic word in dark, hollow places.",
            "There is talk of a cake. They say the cake is not to be trusted.",
            "Ask the universe for the meaning of life — answer in a single number.",
            "Pilots like to do a certain roll. Try asking for one.",
            "Something with a single eye watches from an impossible angle.",
            "Every programmer's very first words to the world still echo here.",
            "A polite request to a sudo-er might just earn you a sandwich.",
        ]
        self.p("  ─ WHISPERS ─────────────────────", "accent")
        self.p("  This machine is hiding things. A few hints:", "dim")
        for h in random.sample(hints, k=min(3, len(hints))):
            self.p("   • " + h, "text")
        self.p("  (try typing phrases, not just commands...)", "dim")

    def cmd_pkg(self, args):
        if not args or args[0].lower() in ("list", "ls"):
            self.p("  ─ PHOSPHOR PACKAGE REPOSITORY ──", "accent")
            for name, desc in self.PKG_CATALOG.items():
                installed = name in self.packages
                tag = "[installed]" if installed else "[available]"
                self.p(f"  {tag:>12} {name:<14} {desc}", "dim" if installed else "text")
            self.p("  install with:  pkg install <name>", "dim")
            return
        sub = args[0].lower()
        name = args[1] if len(args) > 1 else ""
        if sub == "install":
            if name not in self.PKG_CATALOG:
                self.p(f"  no package named '{name}'. try 'pkg list'.", "err"); return
            if name in self.packages:
                self.p(f"  {name} is already installed.", "dim"); return
            self.p(f"  resolving {name} from phosphor-repo...", "dim")
            bar = 24
            if runtime.INTERACTIVE or runtime.GUI_ACTIVE:
                for i in range(bar + 1):
                    pct = int(i / bar * 100)
                    print("\r" + self.c(f"  downloading [{'#' * i}{'-' * (bar - i)}] {pct:3d}%", "text"), end="")
                    time.sleep(0.04)
                print()
            self.packages.append(name)
            self.save_config()
            self.p(f"  ✔ installed {name}.", "accent")
        elif sub in ("remove", "uninstall", "rm"):
            if name in self.packages:
                self.packages.remove(name); self.save_config()
                self.p(f"  removed {name}.", "accent")
            else:
                self.p(f"  {name} is not installed.", "err")
        elif sub == "installed":
            if not self.packages:
                self.p("  (nothing installed)", "dim"); return
            for n in self.packages:
                self.p("  • " + n, "text")
        else:
            self.p("usage: pkg list | pkg install <name> | pkg remove <name> | pkg installed", "warn")

    def cmd_date(self, args=None):
        self.p("  " + datetime.date.today().strftime("%A, %d %B %Y"), "text")

    def cmd_time(self, args=None):
        self.p("  " + datetime.datetime.now().strftime("%H:%M:%S"), "text")

    def cmd_uptime(self, args=None):
        up = int(time.time() - self.start_time)
        self.p(f"  session uptime: {up // 60}m {up % 60}s", "text")

    def cmd_ver(self, args=None):
        self.p(f"  PHOSPHOR-OS  v{self.VERSION}", "accent")
        self.p("  A fictional retro-terminal simulator written in Python.", "text")
        self.p("  Built-in Python REPL + image-to-ASCII + ~60 commands, now in a GUI window.", "text")

    def cmd_save(self, args=None):
        ok = self.save_disk()
        self.p("  disk saved." if ok else "  save failed.", "accent" if ok else "err")

    def cmd_load(self, args=None):
        self.load_disk()
        self.cwd = []
        self.p("  disk reloaded from host.", "accent")

    def cmd_format(self, args=None):
        self.p("  This wipes the ENTIRE virtual disk. Type 'YES' to confirm: ", "warn", end="")
        try:
            ans = input()
        except EOFError:
            ans = ""
        if ans.strip() == "YES":
            self.disk = _default_disk()
            self.cwd = []
            self.save_disk()
            self.p("  disk formatted. fresh filesystem installed.", "accent")
        else:
            self.p("  format cancelled.", "dim")

    def cmd_reboot(self, args=None):
        self.p("  rebooting...", "warn")
        if runtime.INTERACTIVE:
            time.sleep(0.6)
        self.reboot_requested = True
        self.running = False

    def cmd_exit(self, args=None):
        self.p("  Saving disk and powering off. Goodbye.", "accent")
        self.save_config()
        self.save_scores()
        if runtime.INTERACTIVE:
            for _ in range(3):
                print(self.c(".", "dim"), end="", flush=True)
                time.sleep(0.2)
            print()
        self.running = False
