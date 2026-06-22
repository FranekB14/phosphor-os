"""CoreShell: the engine -- boot, prompt, dispatch, persistence, FS internals."""

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


class CoreShell:
    VERSION = "3.0"

    DISK_FILE = "phosphor_disk.json"

    PKG_CATALOG = {
        "ascii-zoo":    "a pack of extra ASCII animals",
        "extra-themes": "three bonus color schemes (flavor)",
        "hacker-suite": "more theatrical fake-hacking tools",
        "lucky-charm":  "a charm for the slot machine (cosmetic)",
        "retro-sfx":    "imaginary boot chimes and key clicks",
    }

    UPDATE_REPO = "FranekB14/phosphor-os"

    UPDATE_BRANCH = "main"

    SPEC = [
        # --- filesystem ---
        ("ls",     ["dir"],        "files", "ls [path]",           "List directory contents"),
        ("cd",     [],             "files", "cd <path>",           "Change current directory ( .. = up, / = root )"),
        ("pwd",    [],             "files", "pwd",                 "Print working directory"),
        ("tree",   [],             "files", "tree [path]",         "Show directory structure as a tree"),
        ("mkdir",  ["md"],         "files", "mkdir <name>",        "Create a directory"),
        ("rmdir",  [],             "files", "rmdir <name>",        "Remove an empty directory"),
        ("touch",  ["new"],        "files", "touch <file>",        "Create an empty file"),
        ("write",  [],             "files", "write <file> <text>", "Overwrite a file with text"),
        ("append", [],             "files", "append <file> <text>","Append text to a file"),
        ("cat",    ["type"],       "files", "cat <file>",          "Print file contents"),
        ("rm",     ["del"],        "files", "rm <name>",           "Delete a file"),
        ("cp",     ["copy"],       "files", "cp <src> <dst>",      "Copy a file"),
        ("mv",     ["move", "ren"],"files", "mv <src> <dst>",      "Move / rename a file"),
        ("find",   [],             "files", "find <text>",         "Find files whose name contains text"),
        ("grep",   [],             "files", "grep <text> [file]",  "Search text in a file or piped input"),
        ("wc",     [],             "files", "wc [file]",            "Count lines / words / chars (file or pipe)"),
        ("head",   [],             "files", "head [n] [file]",      "Show the first n lines (default 10)"),
        ("tail",   [],             "files", "tail [n] [file]",      "Show the last n lines (default 10)"),
        ("sort",   [],             "files", "sort [file]",          "Sort lines (file or piped input)"),
        ("nl",     [],             "files", "nl [file]",            "Number lines (file or piped input)"),
        ("edit",   ["ed"],         "files", "edit <file>",         "Edit a file in a simple line editor"),
        # --- tools ---
        ("python", ["py"],         "tools", "python",              "Drop into a real Python interpreter"),
        ("img2ascii",["ascii","img"],"tools","img2ascii <path> [w] [--color] [--invert] [--save f]",
                                                                   "Convert an image into ASCII art"),
        ("calc",   [],             "tools", "calc <expression>",   "Evaluate a math expression"),
        ("banner", [],             "tools", "banner <text>",       "Print BIG block-letter text"),
        ("echo",   [],             "tools", "echo <text>",         "Print text"),
        ("rev",    [],             "tools", "rev <text>",          "Reverse text"),
        ("upper",  [],             "tools", "upper <text>",        "Uppercase text"),
        ("lower",  [],             "tools", "lower <text>",        "Lowercase text"),
        ("roll",   ["dice"],       "tools", "roll [NdM]",          "Roll dice, e.g. roll 2d6"),
        ("flip",   [],             "tools", "flip",                "Flip a coin"),
        ("convert",["conv","unit"],"tools", "convert <n> <from> <to>", "Convert units (length / weight / temp)"),
        ("todo",   ["task","tasks"],"tools","todo [add|done|rm|clear]", "A simple saved to-do list"),
        # --- system ---
        ("help",   ["?"],          "system","help [command]",     "Show commands or help for one command"),
        ("clear",  ["cls"],        "system","clear",              "Clear the screen"),
        ("man",    ["manual"],     "system","man <command>",      "Show the manual page for a command"),
        ("theme",  ["color"],      "system","theme [name]",       "Change color theme"),
        ("sysinfo",["neofetch"],   "system","sysinfo",            "Show a stylized system info panel"),
        ("history",[],             "system","history",            "Show command history"),
        ("alias",  [],             "system","alias [name=cmd]",   "List or define a command alias (saved)"),
        ("unalias",[],             "system","unalias <name>",     "Remove an alias"),
        ("set",    ["setenv"],     "system","set [NAME=value]",   "List or set an environment variable (saved)"),
        ("unset",  [],             "system","unset <NAME>",       "Remove an environment variable"),
        ("run",    ["batch","do"], "system","run <file>",         "Run a file of commands (batch script)"),
        ("update", ["upgrade"],    "system","update [--check] [--force] [--repo u/r]",
                                                                   "Update PHOSPHOR-OS from its GitHub distro"),
        ("pkg",    ["package"],     "system","pkg [list|install|remove] <name>", "The (fake) package manager"),
        ("secrets",["secret"],     "system","secrets",             "Hints that the OS is hiding something"),
        ("scores", [],             "system","scores",             "Show your best game scores"),
        ("setname",["rename"],     "system","setname <name>",     "Change your username (saved)"),
        ("whoami", [],             "system","whoami",             "Show current user"),
        ("date",   [],             "system","date",               "Show current date"),
        ("time",   [],             "system","time",               "Show current time"),
        ("uptime", [],             "system","uptime",             "Show how long this session has run"),
        ("ver",    ["about"],      "system","ver",                "Show OS version / about"),
        ("save",   [],             "system","save",               "Save the virtual disk to host"),
        ("load",   [],             "system","load",               "Reload the virtual disk from host"),
        ("format", [],             "system","format",             "Wipe the virtual disk (asks first)"),
        ("reboot", [],             "system","reboot",             "Restart the simulator"),
        ("exit",   ["shutdown","quit"],"system","exit",          "Power off and leave"),
        # --- users & permissions (Phase 5) ---
        ("login",  ["signin"],     "users", "login [user]",       "Log in as a user (asks for a password)"),
        ("logout", ["signout"],    "users", "logout",             "Log out and return to the login prompt"),
        ("su",     [],             "users", "su [user]",          "Switch user (root if none given)"),
        ("sudo",   [],             "users", "sudo <command>",     "Run a single command as root"),
        ("passwd", ["password"],   "users", "passwd [user]",      "Set or change a password"),
        ("useradd",["adduser"],    "users", "useradd <name>",     "Create a new user account (admin)"),
        ("userdel",["deluser"],    "users", "userdel <name>",     "Delete a user account (admin)"),
        ("users",  ["who"],        "users", "users",              "List the user accounts"),
        ("id",     [],             "users", "id",                 "Show your user / group ids"),
        ("chmod",  [],             "users", "chmod <mode> <file>","Change a file's permission bits (e.g. 644)"),
        ("chown",  [],             "users", "chown <user> <file>","Change a file's owner"),
        # --- network (Phase 4) ---
        ("ipconfig",["ifconfig","ip"],"network","ipconfig",       "Show network config (incl. your real public IP)"),
        ("myip",   ["whatismyip","publicip"],"network","myip",    "Show your real public IP (VPN-aware)"),
        ("ping",   [],             "network","ping <host>",       "Ping a host on the (simulated) network"),
        ("nslookup",["dig","resolve"],"network","nslookup <host>","Resolve a hostname to an address"),
        ("scan",   ["netscan","nmap"],"network","scan",           "Scan the local segment for live hosts"),
        ("netstat",["ports"],      "network","netstat",           "Show active network connections"),
        ("route",  [],             "network","route",             "Show the IP routing table"),
        ("wget",   ["curl","fetch"],"network","wget <host> [--save f]","Download a page from a network host"),
        ("telnet", ["connect"],    "network","telnet <host>",     "Open a session to a network host"),
        # --- toys ---
        ("matrix", [],             "toys",  "matrix [frames]",     "Digital rain effect"),
        ("hack",   [],             "toys",  "hack <target>",       "Totally real hacking sequence ;)"),
        ("cowsay", [],             "toys",  "cowsay <text>",       "A cow says something wise"),
        ("fortune",[],             "toys",  "fortune",             "Print a random fortune"),
        ("glitch", [],             "toys",  "glitch <text>",       "Render text with corrupted glitches"),
        # --- more tools ---
        ("morse",  [],             "tools", "morse <text|code>",   "Encode text to Morse, or decode . - back"),
        ("leet",   ["1337"],       "tools", "leet <text>",         "Translate text into l33tspeak"),
        ("rot13",  [],             "tools", "rot13 <text>",         "ROT13 cipher (run twice to undo)"),
        ("bases",  ["base"],       "tools", "bases <number>",      "Show a number in dec / bin / oct / hex"),
        ("asciitable", ["chars"],  "tools", "asciitable",          "Print the printable ASCII table"),
        # --- more toys ---
        ("eightball", ["8ball"],   "toys",  "8ball <question>",    "Ask the magic 8-ball a question"),
        ("joke",   [],             "toys",  "joke",                "Tell a (bad) programmer joke"),
        ("rainbow",[],             "toys",  "rainbow <text>",      "Print text in rainbow colors"),
        ("slot",   ["slots"],      "toys",  "slot",                "Spin the slot machine"),
        ("fire",   [],             "toys",  "fire [frames]",       "A cozy ASCII campfire"),
        ("aquarium", ["fish"],     "toys",  "aquarium [frames]",   "A little ASCII fish tank"),
        ("clock",  [],             "toys",  "clock",               "Show the time as a big ASCII clock"),
        ("screensaver", ["saver"], "toys",  "screensaver",         "Run a random screensaver animation"),
        # --- games ---
        ("guess",  [],             "games", "guess",               "Guess-the-number game (1-100)"),
        ("rps",    [],             "games", "rps",                 "Rock paper scissors, best of 3"),
        ("hangman",[],             "games", "hangman",             "Classic hangman word game"),
        ("ttt",    ["tictactoe"],  "games", "ttt",                 "Tic-tac-toe versus the computer"),
        ("quiz",   ["trivia"],     "games", "quiz",                "A quick 5-question trivia quiz"),
        ("wordle", ["phosdle"],    "games", "wordle",              "Guess the 5-letter word in 6 tries"),
        ("2048",   [],             "games", "2048",                "Slide and merge tiles to reach 2048"),
        ("minesweeper", ["mines"], "games", "minesweeper",         "Clear the field without hitting a mine"),
        ("blackjack", ["21"],      "games", "blackjack",           "Beat the dealer to 21 without busting"),
        ("snake",  [],             "games", "snake",               "Steer the snake, eat, grow, don't crash"),
        ("tetris", [],             "games", "tetris",              "Stack falling blocks and clear lines"),
        ("solitaire", ["klondike"],"games", "solitaire",           "Klondike solitaire with a deck of cards"),
    ]

    def __init__(self, input_fn=input):
        self.input_fn = input_fn        # pluggable: builtin input, or the GUI's
        self.theme_name = "phosphor"
        self.theme = THEMES[self.theme_name]
        self.user = (os.environ.get("USER") or os.environ.get("USERNAME") or "operator").lower()
        self.history = []
        self.start_time = time.time()
        self.running = True
        self.reboot_requested = False
        self.disk = None
        self.cwd = []            # path as list of dir names, [] = root
        self.disk_path = os.path.join(app_data_dir(), self.DISK_FILE)
        self.config_path = os.path.join(app_data_dir(), "phosphor_config.json")
        self.scores_path = os.path.join(app_data_dir(), "phosphor_scores.json")
        self.scores = {}
        self.aliases = {}        # user-defined command aliases (Phase 2)
        self.env = {}            # user environment variables (Phase 2)
        self.todos = []          # to-do list items (Phase 3)
        self.packages = []       # installed fake packages (Phase 3)
        self._pipe_in = None     # text piped into the current command, or None
        self._batch_depth = 0    # guard against runaway batch-script recursion
        self._interrupt = False  # set by the GUI on any key to wake a screensaver
        self._screensaver = False  # True while a full-screen screensaver runs
        self.term_size = None    # (cols, rows) reported by the GUI, or None
        self._gui_saver = None   # GUI installs a callback to open a saver window
        self.update_repo = self.UPDATE_REPO
        self.update_branch = self.UPDATE_BRANCH
        self.uid = 1000          # effective user id (0 = root); set by _init_accounts
        self.accounts = {}       # username -> {pw, uid, admin, home}  (Phase 5)
        self.accounts_path = os.path.join(app_data_dir(), "phosphor_users.json")
        # build command dispatch (name/alias -> (handler, spec))
        self.commands = {}
        for primary, aliases, group, usage, desc in self.SPEC:
            handler = getattr(self, "cmd_" + primary)
            meta = (primary, group, usage, desc)
            for name in [primary] + aliases:
                self.commands[name] = (handler, meta)
        self.load_disk()
        self.load_config()
        self.load_scores()
        self._init_accounts()

    def load_config(self):
        try:
            with open(self.config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            name = cfg.get("theme")
            if name in THEMES:
                self.theme_name = name
                self.theme = THEMES[name]
            if cfg.get("user"):
                self.user = cfg["user"]
            if isinstance(cfg.get("aliases"), dict):
                self.aliases = {str(k): str(v) for k, v in cfg["aliases"].items()}
            if isinstance(cfg.get("env"), dict):
                self.env = {str(k): str(v) for k, v in cfg["env"].items()}
            if isinstance(cfg.get("todos"), list):
                self.todos = [t for t in cfg["todos"] if isinstance(t, dict) and "text" in t]
            if isinstance(cfg.get("packages"), list):
                self.packages = [str(p) for p in cfg["packages"]]
            if cfg.get("update_repo"):
                self.update_repo = cfg["update_repo"]
            if cfg.get("update_branch"):
                self.update_branch = cfg["update_branch"]
        except Exception:
            pass

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"theme": self.theme_name, "user": self.user,
                           "aliases": self.aliases, "env": self.env,
                           "todos": self.todos, "packages": self.packages,
                           "update_repo": self.update_repo,
                           "update_branch": self.update_branch}, f)
        except Exception:
            pass

    def load_scores(self):
        try:
            with open(self.scores_path, encoding="utf-8") as f:
                self.scores = json.load(f)
        except Exception:
            self.scores = {}

    def save_scores(self):
        try:
            with open(self.scores_path, "w", encoding="utf-8") as f:
                json.dump(self.scores, f)
        except Exception:
            pass

    def record_score(self, game, value, mode="max"):
        """Record a result. mode='max' keeps the highest, 'min' the lowest,
        'count' increments a tally."""
        cur = self.scores.get(game)
        if mode == "count":
            self.scores[game] = (cur or 0) + value
        elif cur is None or (mode == "max" and value > cur) or (mode == "min" and value < cur):
            self.scores[game] = value
            self.save_scores()
            return True
        if mode == "count":
            self.save_scores()
        return False

    def c(self, text, role="text"):
        return f"{rgb(*self.theme[role])}{text}{RESET}"

    def p(self, text="", role="text", end="\n"):
        print(self.c(text, role), end=end)

    def _input(self, prompt_text="", role="accent"):
        """Prompt for input inside games/tools. Returns None on EOF/Ctrl-C
        so the caller can bail out cleanly instead of crashing."""
        try:
            return self.input_fn(self.c(prompt_text, role))
        except (EOFError, KeyboardInterrupt, ValueError):
            print()
            return None

    def load_disk(self):
        if os.path.isfile(self.disk_path):
            try:
                with open(self.disk_path, "r", encoding="utf-8") as f:
                    self.disk = json.load(f)
                return
            except Exception:
                pass
        self.disk = _default_disk()

    def save_disk(self):
        try:
            with open(self.disk_path, "w", encoding="utf-8") as f:
                json.dump(self.disk, f)
            return True
        except Exception:
            return False

    def _resolve(self, path):
        """Return a path list for `path`, or None if invalid. Does not check existence."""
        if path is None or path == "":
            return list(self.cwd)
        if path[0] == "~":                       # ~ or ~/... -> the user's home
            path = self._home_of(self.user) + path[1:]
        parts = path.replace("\\", "/").split("/")
        cur = [] if path.startswith("/") else list(self.cwd)
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                if cur:
                    cur.pop()
            else:
                cur.append(part)
        return cur

    def _get_node(self, path_list):
        node = self.disk
        for part in path_list:
            if node["type"] != "dir" or part not in node["children"]:
                return None
            node = node["children"][part]
        return node

    def _parent_and_name(self, path):
        plist = self._resolve(path)
        if not plist:
            return None, None
        return self._get_node(plist[:-1]), plist[-1]

    def _cwd_str(self):
        return "/" + "/".join(self.cwd)

    def boot(self):
        self.cmd_clear()
        logo = r"""
  ╔════════════════════════════════════════════════════════════════════════╗
  ║    ____  _   _  ___  ____  ____  _   _  ___  ____        ___  ____     ║
  ║   |  _ \| | | |/ _ \/ ___||  _ \| | | |/ _ \|  _ \      / _ \/ ___|    ║
  ║   | |_) | |_| | | | \___ \| |_) | |_| | | | | |_) |____| | | \___ \    ║
  ║   |  __/|  _  | |_| |___) |  __/|  _  | |_| |  _ <_____| |_| |___) |   ║
  ║   |_|   |_| |_|\___/|____/|_|   |_| |_|\___/|_| \_\     \___/|____/    ║
  ║                                                                        ║
  ║                   ▓▒░   P H O S P H O R - O S   ░▒▓                    ║
  ╚════════════════════════════════════════════════════════════════════════╝
"""
        for line in logo.splitlines():
            self.p(line, "accent")
            if runtime.INTERACTIVE:
                time.sleep(0.02)
        self.p(f"{'':>6}p h o s p h o r   o p e r a t i n g   s y s t e m   v{self.VERSION}", "dim")
        print()
        post = [
            "BIOS .............. PHOSPHOR Micro-Firmware 2.4",
            "CPU  .............. virtual 8-core @ 4.77 THz",
            "RAM  .............. 640 KB (ought to be enough)",
            "VGA  .............. CRT phosphor display online",
            "DISK .............. mounting virtual volume...",
            "NET  .............. localhost only",
        ]
        for item in post:
            self.p("  [ OK ] " + item, "dim")
            if runtime.INTERACTIVE:
                time.sleep(0.08)
        # progress bar
        if runtime.INTERACTIVE:
            bar = 28
            for i in range(bar + 1):
                fill = "#" * i + "-" * (bar - i)
                pct = int(i / bar * 100)
                print("\r" + self.c(f"  loading kernel [{fill}] {pct:3d}%", "text"), end="")
                time.sleep(0.03)
            print()
        print()
        self.p("  Type 'help' for a list of commands. Type 'exit' to power off.", "accent")
        print()

    def prompt(self):
        path = self.c(self._cwd_str(), "accent")
        who = self.c(f"{self.user}@phosphor", "dim")
        return f"{self.c('[', 'dim')}{who} {path}{self.c(']', 'dim')}{self.c('» ', 'text')}"

    def run(self):
        self.boot()
        if self._needs_login():
            self._login_screen()
            if not self.running:
                self.save_disk()
                return
        else:
            # fresh / password-free system: drop straight in as root
            self._switch_to("root")
            self.p("  logged in as root.  (set a password with 'passwd' to require login)", "dim")
            self.p("", "text")
        self._run_autoexec()
        while self.running:
            try:
                line = self.input_fn(self.prompt())
            except (EOFError, ValueError, OSError):
                # EOF, or stdin exhausted/closed (e.g. after a piped session)
                print()
                break
            except KeyboardInterrupt:
                print()
                continue
            self.dispatch(line)
        self.save_disk()

    def dispatch(self, line, top=True):
        line = line.strip()
        if not line:
            return
        if top:
            self.history.append(line)
        # ---- hidden easter eggs: match the whole normalized phrase ----
        norm = " ".join(line.lower().split()).rstrip("?!.")
        if norm in self.EASTER_EGGS:
            try:
                getattr(self, self.EASTER_EGGS[norm])()
            except Exception as e:
                self.p(f"!! something stirred and then crashed: {e}", "err")
            return
        # ---- expand a leading alias, then parse pipes / redirection ----
        line = self._expand_aliases(line)
        try:
            stages, in_file, out_file, append = self._parse_pipeline(line)
        except ValueError as e:
            self.p(str(e), "err")
            return
        if not stages or not stages[0]:
            return
        # A plain single command (no pipe, no redirection) runs "live" so that
        # games, the Python REPL, and animations keep their interactive I/O.
        if len(stages) == 1 and in_file is None and out_file is None:
            self._run_stage_live(stages[0])
        else:
            self._run_pipeline(stages, in_file, out_file, append)

    def _parse_pipeline(self, line):
        """Split a line into pipeline stages plus < / > / >> redirection."""
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars="|<>")
            lex.whitespace_split = True
            toks = list(lex)
        except ValueError:
            toks = line.split()
        stages, in_file, out_file, append = [[]], None, None, False
        i = 0
        while i < len(toks):
            t = toks[i]
            if t == "|":
                stages.append([])
            elif t in (">", ">>"):
                if i + 1 >= len(toks):
                    raise ValueError("syntax error: expected a file name after '%s'" % t)
                out_file, append = toks[i + 1], (t == ">>")
                i += 1
            elif t == "<":
                if i + 1 >= len(toks):
                    raise ValueError("syntax error: expected a file name after '<'")
                in_file = toks[i + 1]
                i += 1
            else:
                stages[-1].append(t)
            i += 1
        stages = [s for s in stages if s]
        return stages, in_file, out_file, append

    def _expand_aliases(self, line, seen=None):
        seen = seen or set()
        head = line.lstrip().split(None, 1)
        if not head:
            return line
        word = head[0]
        if word in self.aliases and word not in seen:
            seen.add(word)
            rest = head[1] if len(head) > 1 else ""
            expanded = self.aliases[word] + ((" " + rest) if rest else "")
            return self._expand_aliases(expanded, seen)
        return line

    def _get_var(self, name):
        if name in self.env:
            return self.env[name]
        builtins = {"USER": self.user, "VERSION": self.VERSION,
                    "CWD": self._cwd_str(), "THEME": self.theme_name, "HOME": "/"}
        return builtins.get(name, "")

    def _expand_vars(self, token):
        return _VAR_RE.sub(lambda m: self._get_var(m.group(1) or m.group(2)), token)

    def _glob(self, pattern):
        p = pattern.replace("\\", "/")
        if "/" in p:
            dirpart, namepat = p.rsplit("/", 1)
            base = self._resolve(dirpart)
        else:
            dirpart, namepat = "", p
            base = list(self.cwd)
        node = self._get_node(base) if base is not None else None
        if not node or node["type"] != "dir":
            return []
        names = sorted(n for n in node["children"] if fnmatch.fnmatch(n, namepat))
        prefix = (dirpart + "/") if dirpart else ""
        return [prefix + n for n in names]

    def _expand_globs(self, args):
        out = []
        for a in args:
            if any(ch in a for ch in "*?[") and "$" not in a:
                hits = self._glob(a)
                out.extend(hits if hits else [a])
            else:
                out.append(a)
        return out

    def _prepare_args(self, tokens):
        args = [self._expand_vars(t) for t in tokens]
        return self._expand_globs(args)

    def _exec(self, cmd, args):
        entry = self.commands.get(cmd)
        if not entry:
            self.p(f"Unknown command: '{cmd}'.  Type 'help' for the list.", "err")
            close = [n for n in self.commands if n.startswith(cmd[:2])][:3]
            if close:
                self.p("  did you mean: " + ", ".join(sorted(set(close))) + " ?", "dim")
            return
        try:
            entry[0](args)
        except Exception as e:
            self.p(f"!! command crashed: {e}", "err")

    def _run_stage_live(self, tokens):
        self._pipe_in = None
        self._exec(tokens[0].lower(), self._prepare_args(tokens[1:]))

    def _run_pipeline(self, stages, in_file, out_file, append):
        text_in = None
        if in_file is not None:
            node = self._get_node(self._resolve(in_file))
            if not node or node["type"] != "file":
                self.p(f"No such file: {in_file}", "err")
                return
            text_in = node["content"]
        last = ""
        for tokens in stages:
            self._pipe_in = text_in
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                self._exec(tokens[0].lower(), self._prepare_args(tokens[1:]))
            finally:
                sys.stdout = saved
            last = strip_ansi(buf.getvalue())
            text_in = last
        self._pipe_in = None
        if out_file is not None:
            if last and not last.endswith("\n"):
                last += "\n"
            self._write_file(out_file, last, append=append)
        else:
            sys.stdout.write(last)
            if last and not last.endswith("\n"):
                sys.stdout.write("\n")

    def _run_autoexec(self):
        """Run /autoexec.bat at startup if it exists (a retro touch)."""
        node = self._get_node(["autoexec.bat"])
        if node and node["type"] == "file":
            self.p("  [autoexec] running startup script...", "dim")
            self._run_script(node["content"])

    def _run_script(self, text):
        if self._batch_depth > 25:
            self.p("  !! batch recursion too deep -- stopping.", "err")
            return
        self._batch_depth += 1
        try:
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("::"):
                    continue
                self.dispatch(line, top=False)
                if not self.running:
                    break
        finally:
            self._batch_depth -= 1
