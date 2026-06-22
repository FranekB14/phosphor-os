"""UsersMixin: the `users` command group."""

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


class UsersMixin:
    @staticmethod
    def _hash(pw):
        import hashlib
        return hashlib.sha256(("phosphor$" + pw).encode("utf-8")).hexdigest()

    def _init_accounts(self):
        """Load the account table, ensure root + the current user exist, set the
        effective uid, and make sure home + system directories are present."""
        self.accounts = {}
        try:
            if os.path.exists(self.accounts_path):
                with open(self.accounts_path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.accounts = data
        except Exception:
            self.accounts = {}
        if "root" not in self.accounts:
            self.accounts["root"] = {"pw": None, "uid": 0, "admin": True, "home": "/root"}
        if self.user not in self.accounts:
            self.accounts[self.user] = {"pw": None, "uid": 1000, "admin": True,
                                        "home": f"/home/{self.user}"}
        self.uid = self.accounts[self.user].get("uid", 1000)
        self._ensure_system_files()
        self._ensure_home(self.user)
        self.save_accounts()

    def save_accounts(self):
        try:
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f)
        except Exception:
            pass

    def _home_of(self, user):
        acct = self.accounts.get(user)
        if acct and acct.get("home"):
            return acct["home"]
        return "/root" if user == "root" else f"/home/{user}"

    def _is_admin(self, user):
        acct = self.accounts.get(user)
        return bool(acct and (acct.get("admin") or acct.get("uid") == 0))

    def _owner_of(self, node):
        if isinstance(node, dict) and node.get("owner"):
            return node["owner"]
        return self.user

    @staticmethod
    def _mode_str(node):
        mode = node.get("mode")
        if mode is None:
            mode = 0o755 if node.get("type") == "dir" else 0o644
        bits = ""
        for shift in (6, 3, 0):
            triad = (mode >> shift) & 7
            bits += ("r" if triad & 4 else "-")
            bits += ("w" if triad & 2 else "-")
            bits += ("x" if triad & 1 else "-")
        return bits

    def _can(self, node, op):
        """Permission check. Root bypasses; nodes with no explicit owner are
        unrestricted (so existing disks keep working)."""
        if self.uid == 0 or not isinstance(node, dict):
            return True
        owner = node.get("owner")
        if owner is None:
            return True
        mode = node.get("mode")
        if mode is None:
            mode = 0o755 if node.get("type") == "dir" else 0o644
        bit = {"r": 4, "w": 2, "x": 1}[op]
        shift = 6 if owner == self.user else 0
        return bool((mode >> shift) & bit)

    def _ensure_system_files(self):
        if not isinstance(self.disk, dict) or self.disk.get("type") != "dir":
            return
        root = self.disk
        if "etc" not in root["children"]:
            d = _new_dir(); d["owner"] = "root"; d["mode"] = 0o755
            root["children"]["etc"] = d
        etc = root["children"].get("etc")
        if isinstance(etc, dict) and etc.get("type") == "dir" and "shadow" not in etc["children"]:
            f = _new_file("root:x:0:0\n(you really shouldn't be able to read this)\n")
            f["owner"] = "root"; f["mode"] = 0o600
            etc["children"]["shadow"] = f
        if "root" not in root["children"]:
            d = _new_dir(); d["owner"] = "root"; d["mode"] = 0o700
            note = _new_file("if you're reading this without sudo, well done.\n")
            note["owner"] = "root"; note["mode"] = 0o600
            d["children"]["notes.txt"] = note
            root["children"]["root"] = d

    def _ensure_home(self, user):
        if not isinstance(self.disk, dict) or self.disk.get("type") != "dir":
            return self._home_of(user)
        if user == "root":
            return "/root"
        root = self.disk
        if "home" not in root["children"]:
            h = _new_dir(); h["owner"] = "root"; h["mode"] = 0o755
            root["children"]["home"] = h
        home = root["children"].get("home")
        if isinstance(home, dict) and home.get("type") == "dir" and user not in home["children"]:
            d = _new_dir(); d["owner"] = user; d["mode"] = 0o755
            home["children"][user] = d
        return f"/home/{user}"

    def _needs_login(self):
        """A login prompt only matters once a password exists somewhere. On a
        fresh, password-free system we just drop straight in as root."""
        return any(a.get("pw") for a in self.accounts.values())

    def _login_screen(self):
        """Force a login before the shell starts. Loops until a valid account
        and password are given (or the input stream ends)."""
        self.p("", "text")
        self.p("  ── PHOSPHOR-OS login ──────────────────────────", "accent")
        attempts = 0
        while self.running:
            name = self._input("  login: ", "accent")
            if name is None:                     # EOF / Ctrl-C -> give up
                self.running = False
                return
            name = name.strip().lower()
            if not name:
                continue
            acct = self.accounts.get(name)
            need_pw = acct.get("pw") if acct else None
            entered = ""
            if need_pw is not None:
                entered = self._input("  password: ", "dim")
                if entered is None:
                    self.running = False
                    return
            if acct and (need_pw is None or self._hash(entered) == need_pw):
                self._switch_to(name)
                self.p(f"  login successful — welcome, {name}.", "accent")
                self.p("", "text")
                return
            attempts += 1
            self.p("  login incorrect", "err")
            if attempts >= 5:
                self.p("  too many failed attempts — locking console.", "err")
                self.running = False
                return

    def _switch_to(self, user):
        self.user = user
        self.uid = self.accounts[user].get("uid", 1000)
        self._ensure_home(user)
        self.cwd = self._resolve(self._home_of(user))
        self.save_config()

    def cmd_login(self, args=None):
        args = args or []
        name = (args[0] if args else self._input("  login: ", "accent"))
        if name is None:
            return
        name = name.strip().lower()
        if not name:
            return
        if name not in self.accounts:
            self.p(f"  login: no such user '{name}'", "err"); return
        acct = self.accounts[name]
        if acct.get("pw"):
            pw = self._input("  password: ", "dim")
            if pw is None or self._hash(pw) != acct["pw"]:
                self.p("  login incorrect", "err"); return
        self._switch_to(name)
        self.p(f"  welcome, {name}.", "accent")

    def cmd_logout(self, args=None):
        self.p(f"  logging out {self.user}...", "dim")
        self.cmd_login([])

    def cmd_su(self, args=None):
        args = args or []
        name = (args[0].lower() if args else "root")
        if name not in self.accounts:
            self.p(f"  su: user {name} does not exist", "err"); return
        acct = self.accounts[name]
        # root can become anyone without a password; otherwise a password is required
        if self.uid != 0 and acct.get("pw"):
            pw = self._input("  password: ", "dim")
            if pw is None or self._hash(pw) != acct["pw"]:
                self.p("  su: authentication failure", "err"); return
        self._switch_to(name)
        self.p(f"  now: {name}" + ("  (root)" if self.uid == 0 else ""), "accent")

    def cmd_sudo(self, args=None):
        args = args or []
        if not args:
            self.p("usage: sudo <command>", "warn"); return
        if self.uid != 0 and not self._is_admin(self.user):
            self.p(f"  {self.user} is not in the sudoers file.  "
                   f"This incident will be reported.", "err"); return
        saved = self.uid
        self.uid = 0
        try:
            self.dispatch(" ".join(args), top=False)
        finally:
            self.uid = saved

    def cmd_passwd(self, args=None):
        args = args or []
        target = (args[0].lower() if args else self.user)
        if target not in self.accounts:
            self.p(f"  passwd: user '{target}' not found", "err"); return
        if target != self.user and self.uid != 0 and not self._is_admin(self.user):
            self.p("  passwd: you may only change your own password", "err"); return
        new = self._input(f"  new password for {target}: ", "dim")
        if new is None:
            return
        new = new.strip()
        if not new:
            self.accounts[target]["pw"] = None
            self.save_accounts()
            self.p("  password cleared (no password set).", "warn"); return
        confirm = self._input("  retype password: ", "dim")
        if confirm is None or confirm.strip() != new:
            self.p("  passwords do not match — unchanged.", "err"); return
        self.accounts[target]["pw"] = self._hash(new)
        self.save_accounts()
        self.p(f"  password updated for {target}.", "accent")

    def cmd_useradd(self, args=None):
        args = args or []
        if self.uid != 0 and not self._is_admin(self.user):
            self.p("  useradd: permission denied (admin only)", "err"); return
        if not args:
            self.p("usage: useradd <name>", "warn"); return
        name = args[0].strip().lower()[:20]
        if not name.isidentifier():
            self.p("  useradd: name must be letters/digits/underscore", "err"); return
        if name in self.accounts:
            self.p(f"  useradd: '{name}' already exists", "err"); return
        uid = max([a.get("uid", 1000) for a in self.accounts.values()] + [1000]) + 1
        self.accounts[name] = {"pw": None, "uid": uid, "admin": False,
                               "home": f"/home/{name}"}
        self._ensure_home(name)
        self.save_accounts()
        self.p(f"  created user '{name}' (uid {uid}), home /home/{name}.", "accent")
        self.p(f"  set a password with:  passwd {name}", "dim")

    def cmd_userdel(self, args=None):
        args = args or []
        if self.uid != 0 and not self._is_admin(self.user):
            self.p("  userdel: permission denied (admin only)", "err"); return
        if not args:
            self.p("usage: userdel <name>", "warn"); return
        name = args[0].strip().lower()
        if name == "root":
            self.p("  userdel: refusing to remove root", "err"); return
        if name == self.user:
            self.p("  userdel: you can't delete the account you're logged into", "err"); return
        if name not in self.accounts:
            self.p(f"  userdel: no such user '{name}'", "err"); return
        del self.accounts[name]
        self.save_accounts()
        self.p(f"  removed user '{name}'. (their home directory was left in place)", "accent")

    def cmd_users(self, args=None):
        self.p("  USER         UID   ADMIN   HOME", "accent")
        self.p("  " + "─" * 44, "dim")
        for name in sorted(self.accounts, key=lambda n: self.accounts[n].get("uid", 9999)):
            a = self.accounts[name]
            here = " *" if name == self.user else ""
            self.p(f"  {name:<12} {a.get('uid', '?'):<5} "
                   f"{'yes' if a.get('admin') or a.get('uid') == 0 else 'no':<7} "
                   f"{a.get('home', '')}{here}", "text")

    def cmd_id(self, args=None):
        grp = "wheel" if (self.uid == 0 or self._is_admin(self.user)) else "users"
        self.p(f"  uid={self.uid}({self.user}) gid={self.uid}({grp})", "text")

    def cmd_chmod(self, args=None):
        args = args or []
        if len(args) < 2:
            self.p("usage: chmod <octal mode> <file>   e.g. chmod 600 secret.txt", "warn"); return
        try:
            mode = int(args[0], 8)
        except ValueError:
            self.p("  chmod: mode must be octal, e.g. 644 or 755", "err"); return
        node = self._get_node(self._resolve(args[1]))
        if node is None:
            self.p(f"  chmod: cannot access '{args[1]}'", "err"); return
        if self.uid != 0 and self._owner_of(node) != self.user:
            self.p("  chmod: operation not permitted (not the owner)", "err"); return
        node["mode"] = mode & 0o777
        if "owner" not in node:
            node["owner"] = self.user
        self.p(f"  mode of '{args[1]}' set to {oct(node['mode'])[2:]} "
               f"({self._mode_str(node)})", "accent")

    def cmd_chown(self, args=None):
        args = args or []
        if len(args) < 2:
            self.p("usage: chown <user> <file>", "warn"); return
        newowner = args[0].lower()
        if newowner not in self.accounts:
            self.p(f"  chown: invalid user: '{newowner}'", "err"); return
        node = self._get_node(self._resolve(args[1]))
        if node is None:
            self.p(f"  chown: cannot access '{args[1]}'", "err"); return
        if self.uid != 0 and not self._is_admin(self.user):
            self.p("  chown: operation not permitted (admin only)", "err"); return
        node["owner"] = newowner
        if "mode" not in node:
            node["mode"] = 0o755 if node.get("type") == "dir" else 0o644
        self.p(f"  owner of '{args[1]}' changed to {newowner}.", "accent")
