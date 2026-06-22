"""FilesMixin: the `files` command group."""

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


class FilesMixin:
    def cmd_ls(self, args=None):
        args = args or []
        # 0 or 1 directory arg -> classic directory listing
        if len(args) <= 1:
            node = self._get_node(self._resolve(args[0] if args else None))
            if node is not None and node["type"] == "dir":
                self._ls_dir(node)
                return
        # multiple args, or a non-directory (e.g. from a glob like *.txt) ->
        # list each path that exists
        any_shown = False
        for path in args:
            node = self._get_node(self._resolve(path))
            if node is None:
                self.p(f"  not found: {path}", "err")
            elif node["type"] == "dir":
                self.p(f"  <DIR>  {path}/", "accent"); any_shown = True
            else:
                self.p(f"  {len(node['content']):>6}  {path}", "text"); any_shown = True
        if not any_shown and not args:
            self.p("  (empty)", "dim")

    def _ls_dir(self, node):
        children = node["children"]
        if not children:
            self.p("  (empty)", "dim")
            return
        dirs = sorted(k for k, v in children.items() if v["type"] == "dir")
        files = sorted(k for k, v in children.items() if v["type"] == "file")
        for d in dirs:
            self.p(f"  <DIR>  {d}/", "accent")
        for f in files:
            size = len(children[f]["content"])
            self.p(f"  {size:>6}  {f}", "text")

    def cmd_cd(self, args):
        if not args:
            self.cwd = []
            return
        target = self._resolve(args[0])
        node = self._get_node(target)
        if node is None or node["type"] != "dir":
            self.p(f"No such directory: {args[0]}", "err")
            return
        self.cwd = target

    def cmd_pwd(self, args=None):
        self.p("  " + self._cwd_str(), "text")

    def cmd_tree(self, args=None):
        args = args or []
        start = self._resolve(args[0] if args else None)
        node = self._get_node(start)
        if node is None or node["type"] != "dir":
            self.p("Not a directory.", "err")
            return
        root_label = "/" + "/".join(start) if start else "/"
        self.p(root_label, "accent")

        def walk(n, prefix=""):
            items = sorted(n["children"].items(),
                           key=lambda kv: (kv[1]["type"] != "dir", kv[0]))
            for i, (name, child) in enumerate(items):
                last = i == len(items) - 1
                branch = "└── " if last else "├── "
                label = name + ("/" if child["type"] == "dir" else "")
                role = "accent" if child["type"] == "dir" else "text"
                self.p(prefix + branch + label, role)
                if child["type"] == "dir":
                    walk(child, prefix + ("    " if last else "│   "))
        walk(node)

    def cmd_mkdir(self, args):
        if not args:
            self.p("usage: mkdir <name>", "warn"); return
        parent, name = self._parent_and_name(args[0])
        if parent is None or parent["type"] != "dir":
            self.p("Invalid path.", "err"); return
        if name in parent["children"]:
            self.p("Already exists.", "err"); return
        parent["children"][name] = _new_dir()

    def cmd_rmdir(self, args):
        if not args:
            self.p("usage: rmdir <name>", "warn"); return
        parent, name = self._parent_and_name(args[0])
        node = parent["children"].get(name) if parent else None
        if not node or node["type"] != "dir":
            self.p("No such directory.", "err"); return
        if node["children"]:
            self.p("Directory not empty.", "err"); return
        del parent["children"][name]

    def cmd_touch(self, args):
        if not args:
            self.p("usage: touch <file>", "warn"); return
        parent, name = self._parent_and_name(args[0])
        if parent is None or parent["type"] != "dir":
            self.p("Invalid path.", "err"); return
        parent["children"].setdefault(name, _new_file(""))

    def _write_file(self, path, text, append=False):
        parent, name = self._parent_and_name(path)
        if parent is None or parent["type"] != "dir":
            self.p("Invalid path.", "err"); return
        existing = parent["children"].get(name)
        base = existing["content"] if (append and existing and existing["type"] == "file") else ""
        parent["children"][name] = _new_file(base + text)

    def cmd_write(self, args):
        if len(args) < 1:
            self.p("usage: write <file> <text>", "warn"); return
        self._write_file(args[0], " ".join(args[1:]) + "\n", append=False)

    def cmd_append(self, args):
        if len(args) < 1:
            self.p("usage: append <file> <text>", "warn"); return
        self._write_file(args[0], " ".join(args[1:]) + "\n", append=True)

    def cmd_cat(self, args):
        if not args:
            if self._pipe_in is not None:
                for line in self._pipe_in.splitlines():
                    self.p(line, "text")
            else:
                self.p("usage: cat <file>", "warn")
            return
        for path in args:
            node = self._get_node(self._resolve(path))
            if not node or node["type"] != "file":
                self.p(f"No such file: {path}", "err"); continue
            if not node["content"]:
                self.p("  (empty file)", "dim"); continue
            for line in node["content"].splitlines():
                self.p(line, "text")

    def cmd_edit(self, args):
        if not args:
            self.p("usage: edit <file>", "warn"); return
        path = args[0]
        node = self._get_node(self._resolve(path))
        if node and node["type"] == "dir":
            self.p("That's a directory.", "err"); return
        lines = node["content"].splitlines() if (node and node["type"] == "file") else []
        self.p(f"  -- editing {path} --  ('?' for help, 'wq' to save & quit)", "accent")
        self._edit_show(lines)
        dirty = False
        while True:
            raw = self._input("edit> ", "dim")
            if raw is None:
                self.p("  (aborted, not saved)", "warn"); return
            parts = raw.strip().split(None, 1)
            if not parts:
                continue
            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""
            if op in ("?", "help"):
                self.p("  a=append lines (end with '.')   i N=insert before line N", "dim")
                self.p("  d N=delete line N   r N text=replace line N   l=list", "dim")
                self.p("  w=save   q=quit   wq=save & quit", "dim")
            elif op == "l":
                self._edit_show(lines)
            elif op == "a":
                self.p("  (type lines; a single '.' ends input)", "dim")
                while True:
                    ln = self._input("  + ", "dim")
                    if ln is None or ln.strip() == ".":
                        break
                    lines.append(ln); dirty = True
            elif op == "i":
                num = rest.split(None, 1)
                idx = (int(num[0]) - 1) if num and num[0].isdigit() else len(lines)
                lines.insert(max(0, idx), num[1] if len(num) > 1 else "")
                dirty = True
            elif op == "d" and rest.strip().isdigit():
                i = int(rest.strip()) - 1
                if 0 <= i < len(lines):
                    lines.pop(i); dirty = True
                else:
                    self.p("  no such line.", "err")
            elif op == "r":
                num = rest.split(None, 1)
                if num and num[0].isdigit() and 0 <= int(num[0]) - 1 < len(lines):
                    lines[int(num[0]) - 1] = num[1] if len(num) > 1 else ""
                    dirty = True
                else:
                    self.p("  usage: r <line#> <new text>", "warn")
            elif op in ("w", "wq"):
                self._write_file(path, "\n".join(lines) + ("\n" if lines else ""), append=False)
                dirty = False
                self.p(f"  saved {len(lines)} line(s) to {path}.", "accent")
                if op == "wq":
                    return
            elif op == "q":
                if dirty:
                    self.p("  unsaved changes -- use 'wq' to save, or 'q!' to discard.", "warn")
                else:
                    return
            elif op == "q!":
                return
            else:
                self.p("  unknown editor command -- '?' for help.", "dim")

    def _edit_show(self, lines):
        if not lines:
            self.p("  (empty file)", "dim"); return
        for i, line in enumerate(lines, 1):
            self.p(f"  {i:>3} | {line}", "text")

    def cmd_rm(self, args):
        if not args:
            self.p("usage: rm <name> [name ...]", "warn"); return
        for path in args:
            parent, name = self._parent_and_name(path)
            node = parent["children"].get(name) if parent else None
            if not node or node["type"] != "file":
                self.p(f"No such file: {path} (use rmdir for directories).", "err")
                continue
            del parent["children"][name]

    def cmd_cp(self, args):
        if len(args) < 2:
            self.p("usage: cp <src> <dst>", "warn"); return
        src = self._get_node(self._resolve(args[0]))
        if not src or src["type"] != "file":
            self.p("Source file not found.", "err"); return
        parent, name = self._parent_and_name(args[1])
        if parent is None:
            self.p("Invalid destination.", "err"); return
        parent["children"][name] = _new_file(src["content"])

    def cmd_mv(self, args):
        if len(args) < 2:
            self.p("usage: mv <src> <dst>", "warn"); return
        sp, sn = self._parent_and_name(args[0])
        node = sp["children"].get(sn) if sp else None
        if not node:
            self.p("Source not found.", "err"); return
        dp, dn = self._parent_and_name(args[1])
        if dp is None:
            self.p("Invalid destination.", "err"); return
        dp["children"][dn] = node
        del sp["children"][sn]

    def cmd_find(self, args):
        if not args:
            self.p("usage: find <text>", "warn"); return
        needle = args[0].lower()
        hits = []

        def walk(node, path):
            for name, child in node["children"].items():
                full = path + "/" + name
                if needle in name.lower():
                    hits.append(full + ("/" if child["type"] == "dir" else ""))
                if child["type"] == "dir":
                    walk(child, full)
        walk(self.disk, "")
        if not hits:
            self.p("  no matches.", "dim"); return
        for h in hits:
            self.p("  " + h, "text")

    def _source_text(self, file_arg):
        """Return text from a file arg, else from piped input, else None."""
        if file_arg is not None:
            node = self._get_node(self._resolve(file_arg))
            if not node or node["type"] != "file":
                self.p("No such file.", "err")
                return None
            return node["content"]
        if self._pipe_in is not None:
            return self._pipe_in
        return None

    def cmd_grep(self, args):
        if not args:
            self.p("usage: grep <text> [file]", "warn"); return
        needle = args[0]
        text = self._source_text(args[1] if len(args) > 1 else None)
        if text is None:
            if len(args) < 2:
                self.p("usage: grep <text> <file>   (or pipe text in)", "warn")
            return
        found = False
        for i, line in enumerate(text.splitlines(), 1):
            if needle.lower() in line.lower():
                self.p(f"  {i:>4}: {line}", "text")
                found = True
        if not found:
            self.p("  no matches.", "dim")

    def cmd_wc(self, args):
        text = self._source_text(args[0] if args else None)
        if text is None:
            if not args:
                self.p("usage: wc <file>   (or pipe text in)", "warn")
            return
        self.p(f"  lines: {len(text.splitlines())}   words: {len(text.split())}"
               f"   chars: {len(text)}", "text")

    def cmd_head(self, args):
        n, file_arg = 10, None
        for a in args:
            if a.lstrip("-").isdigit():
                n = int(a.lstrip("-"))
            else:
                file_arg = a
        text = self._source_text(file_arg)
        if text is None:
            if not args:
                self.p("usage: head [n] <file>   (or pipe text in)", "warn")
            return
        for line in text.splitlines()[:max(0, n)]:
            self.p(line, "text")

    def cmd_tail(self, args):
        n, file_arg = 10, None
        for a in args:
            if a.lstrip("-").isdigit():
                n = int(a.lstrip("-"))
            else:
                file_arg = a
        text = self._source_text(file_arg)
        if text is None:
            if not args:
                self.p("usage: tail [n] <file>   (or pipe text in)", "warn")
            return
        for line in text.splitlines()[-max(0, n):] if n else []:
            self.p(line, "text")

    def cmd_sort(self, args):
        text = self._source_text(args[0] if args else None)
        if text is None:
            if not args:
                self.p("usage: sort <file>   (or pipe text in)", "warn")
            return
        for line in sorted(text.splitlines(), key=str.lower):
            self.p(line, "text")

    def cmd_nl(self, args):
        text = self._source_text(args[0] if args else None)
        if text is None:
            if not args:
                self.p("usage: nl <file>   (or pipe text in)", "warn")
            return
        for i, line in enumerate(text.splitlines(), 1):
            self.p(f"  {i:>4}  {line}", "text")
