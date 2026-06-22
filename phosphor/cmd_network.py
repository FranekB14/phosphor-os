"""NetworkMixin: the `network` command group."""

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


class NetworkMixin:
    NET_HOSTS = {
        "gateway.phosphor.net": ("10.0.0.1",      "Local gateway — the only way out."),
        "archive.retronet.org": ("198.51.100.7",  "A dusty file archive from the old net."),
        "bbs.nightcity.bbs":    ("203.0.113.42",  "An after-hours bulletin board. Still up, somehow."),
        "oracle.deepnet":       ("198.51.100.66", "It answers questions. It asks more."),
        "void.null":            ("127.0.0.66",    "There is nothing here. Keep looking."),
        "the-angle.eye":        ("0.0.0.0",       "??? — this should not resolve."),
    }

    NET_PAGES = {
        "gateway.phosphor.net":
            "PHOSPHOR GATEWAY v3\n"
            "  routes: 6 known hosts\n"
            "  uplink: ESTABLISHED (origin unknown)\n"
            "  notice: do not query the-angle.eye",
        "archive.retronet.org":
            "== RETRONET FILE ARCHIVE ==\n"
            "  /warez/ ........ (rotted)\n"
            "  /demos/ ........ 4 files\n"
            "  /readme.txt .... 'we were here first. you are late.'",
        "bbs.nightcity.bbs":
            "*** NIGHT CITY BBS — 2400 baud ***\n"
            "  [M]essages  [F]iles  [D]oor games  [G]oodbye\n"
            "  last caller: you, 11 years ago. welcome back.",
        "oracle.deepnet":
            "the oracle is listening.\n"
            "  ask, and the line will answer.\n"
            "  (it already knows what you typed.)",
        "void.null":
            " ",
    }

    NET_BANNERS = {
        "gateway.phosphor.net": "PHOSPHOR-OS gateway. Authorized phantoms only.",
        "archive.retronet.org": "RETRONET archive login:  (anonymous accepted)\nwelcome, stranger.",
        "bbs.nightcity.bbs":    "Connected to NIGHT CITY BBS.\nThe sysop logged off in 1996 and never came back.",
        "oracle.deepnet":       "ORACLE> you have one question. choose it carefully.",
        "void.null":            "(the connection opens onto nothing)",
    }

    def _local_ip(self):
        """The machine's LAN address. Uses a UDP socket route lookup — no
        packets are actually sent."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            finally:
                s.close()
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def _public_ip(self):
        """The machine's REAL outward-facing IP — i.e. the VPN's exit address
        when a VPN is connected. Returns None if offline."""
        import urllib.request
        for url in ("https://api.ipify.org", "https://ifconfig.me/ip",
                    "https://icanhazip.com", "https://ipinfo.io/ip"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PHOSPHOR-OS"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    ip = r.read().decode("utf-8", "replace").strip()
                if ip and len(ip) <= 45 and all(c in "0123456789abcdefABCDEF.:" for c in ip):
                    return ip
            except Exception:
                continue
        return None

    def _fake_mac(self):
        import hashlib, socket
        h = hashlib.md5(socket.gethostname().encode()).hexdigest()[:12].upper()
        return ":".join(h[i:i + 2] for i in range(0, 12, 2))

    def _resolve_host(self, host):
        host = host.lower()
        if host in self.NET_HOSTS:
            return self.NET_HOSTS[host][0]
        import hashlib
        h = hashlib.md5(host.encode()).digest()
        return f"{(h[0] % 223) + 11}.{h[1]}.{h[2]}.{(h[3] % 254) + 1}"

    def cmd_ipconfig(self, args=None):
        import socket
        host = socket.gethostname()
        lan = self._local_ip()
        gw = (lan.rsplit(".", 1)[0] + ".1") if lan.count(".") == 3 else "10.0.0.1"
        self.p("  PHOSPHOR-OS  Network Configuration", "accent")
        self.p("  " + "─" * 50, "dim")
        self.p(f"   Host Name . . . . . . . . : {host}", "text")
        self.p(f"   Adapter . . . . . . . . . : PHOSPHOR Virtual NIC", "text")
        self.p(f"   Physical Address  . . . . : {self._fake_mac()}", "text")
        self.p(f"   IPv4 Address (LAN). . . . : {lan}", "text")
        self.p(f"   Subnet Mask . . . . . . . : 255.255.255.0", "text")
        self.p(f"   Default Gateway . . . . . : {gw}", "text")
        self.p("   querying public address . . .", "dim")
        pub = self._public_ip()
        if pub:
            self.p(f"   Public Address  . . . . . : {pub}", "accent")
            self.p("   (your real outward-facing IP — your VPN's exit IP if one is active)", "dim")
        else:
            self.p("   Public Address  . . . . . : unreachable (offline?)", "warn")

    def cmd_myip(self, args=None):
        self.p("  querying your public IP address...", "dim")
        pub = self._public_ip()
        if pub:
            self.p(f"  your public IP is  {pub}", "accent")
            self.p("  (this reflects your VPN's exit IP when a VPN is connected)", "dim")
        else:
            self.p("  could not reach the network — are you online?", "warn")

    def cmd_ping(self, args=None):
        args = args or []
        if not args:
            self.p("usage: ping <host>", "warn"); return
        host = args[0].lower()
        ip = self._resolve_host(host)
        flaky = host in ("the-angle.eye", "void.null")
        self.p(f"  PING {host} ({ip}): 56 data bytes", "accent")
        times, lost = [], 0
        for seq in range(4):
            if runtime.INTERACTIVE:
                time.sleep(0.3)
            if random.random() < (0.6 if flaky else 0.04):
                self.p(f"    icmp_seq={seq} : request timed out", "warn"); lost += 1
            else:
                ms = round(random.uniform(6, 90), 1)
                times.append(ms)
                self.p(f"    64 bytes from {ip}: icmp_seq={seq} ttl=64 time={ms} ms", "text")
        self.p(f"  --- {host} ping statistics ---", "accent")
        self.p(f"  4 packets transmitted, {4 - lost} received, {lost * 25}% packet loss", "text")
        if times:
            self.p(f"  rtt min/avg/max = {min(times)}/"
                   f"{round(sum(times) / len(times), 1)}/{max(times)} ms", "dim")
        if flaky and lost == 4:
            self.p("  the host is there. it simply chose not to answer.", "err")

    def cmd_nslookup(self, args=None):
        args = args or []
        if not args:
            self.p("usage: nslookup <host>", "warn"); return
        host = args[0].lower()
        self.p("  Server:   gateway.phosphor.net", "dim")
        self.p("  Address:  10.0.0.1#53", "dim")
        self.p("", "text")
        if host == "the-angle.eye":
            self.p(f"  Name:     {host}", "text")
            self.p("  Address:  it is already inside the resolver", "err"); return
        self.p(f"  Name:     {host}", "text")
        self.p(f"  Address:  {self._resolve_host(host)}", "accent")

    def cmd_scan(self, args=None):
        self.p("  scanning local segment 10.0.0.0/24 for live hosts...", "dim")
        for name, (ip, desc) in self.NET_HOSTS.items():
            if runtime.INTERACTIVE:
                time.sleep(0.12)
            state = "??" if name == "the-angle.eye" else "up"
            self.p(f"    {ip:<16} {name:<24} [{state}]  {desc}", "text")
        self.p(f"  {len(self.NET_HOSTS)} hosts responded.", "accent")
        self.p("  try:  ping <host>  |  wget <host>  |  telnet <host>", "dim")

    def cmd_netstat(self, args=None):
        lan = self._local_ip()
        self.p("  Active Connections", "accent")
        self.p("  Proto  Local Address           Foreign Address          State", "dim")
        rows = [
            ("TCP", f"{lan}:51713", "gateway.phosphor.net:443", "ESTABLISHED"),
            ("TCP", f"{lan}:51714", "archive.retronet.org:21",  "TIME_WAIT"),
            ("TCP", f"{lan}:51720", "oracle.deepnet:6667",      "ESTABLISHED"),
            ("UDP", f"{lan}:137",   "*:*",                      ""),
            ("TCP", "127.0.0.66:0", "the-angle.eye:?",          "WATCHING"),
        ]
        for p, l, f, s in rows:
            self.p(f"  {p:<5}  {l:<23} {f:<24} {s}", "text")

    def cmd_route(self, args=None):
        lan = self._local_ip()
        gw = (lan.rsplit(".", 1)[0] + ".1") if lan.count(".") == 3 else "10.0.0.1"
        self.p("  Kernel IP routing table", "accent")
        self.p("  Destination      Gateway          Genmask          Iface", "dim")
        self.p(f"  0.0.0.0          {gw:<16} 0.0.0.0          eth0", "text")
        self.p(f"  10.0.0.0         0.0.0.0          255.255.255.0    eth0", "text")
        self.p(f"  127.0.0.0        0.0.0.0          255.0.0.0        lo", "text")
        self.p("  0.0.0.0          the-angle.eye    0.0.0.0          ????", "err")

    def cmd_wget(self, args=None):
        args = args or []
        if not args:
            self.p("usage: wget <host> [--save <file>]", "warn"); return
        host = args[0].lower().replace("http://", "").replace("https://", "").split("/")[0]
        self.p(f"  connecting to {host} ({self._resolve_host(host)})...", "dim")
        if runtime.INTERACTIVE:
            time.sleep(0.4)
        page = self.NET_PAGES.get(host)
        if page is None:
            self.p(f"  404 — nothing served at {host}", "warn")
            self.p("  (run 'scan' to see which hosts are out there)", "dim"); return
        self.p(f"  200 OK — {len(page)} bytes received", "accent")
        if "--save" in args:
            i = args.index("--save")
            fname = args[i + 1] if i + 1 < len(args) else "page.txt"
            parent, name = self._parent_and_name(fname)
            if parent is None or parent["type"] != "dir":
                self.p("  bad save path.", "err"); return
            parent["children"][name] = _new_file(page)
            self.save_disk()
            self.p(f"  saved to {fname}", "accent"); return
        self.p("  " + "─" * 50, "dim")
        for line in page.split("\n"):
            self.p("  " + line, "text")

    def cmd_telnet(self, args=None):
        args = args or []
        if not args:
            self.p("usage: telnet <host>", "warn"); return
        host = args[0].lower()
        if host not in self.NET_HOSTS:
            self.p(f"  telnet: unable to connect to {host}: host unknown", "err"); return
        self.p(f"  Trying {self._resolve_host(host)}...", "dim")
        self._snd("dialup")
        if runtime.INTERACTIVE:
            time.sleep(0.5)
        self.p(f"  Connected to {host}.", "accent")
        self._log(f"netd: session opened to {host} ({self._resolve_host(host)})")
        self.p("  Escape character is '^]'.", "dim")
        for line in self.NET_BANNERS.get(host, "(the line is silent)").split("\n"):
            self.p("  " + line, "text")
        if host == "bbs.nightcity.bbs":
            self._session_bbs()
        elif host == "oracle.deepnet":
            self._session_oracle()
        elif host == "the-angle.eye":
            self._session_angle()
        elif host in self._WEB_HOME:
            self.p(f"  this host serves pages — try:  browse {host}", "dim")
        self.p(f"  Connection to {host} closed.", "dim")

    _BBS_BOARDS = {"1": "general", "2": "netrunners", "3": "watching", "4": "trades"}

    _BBS_TITLES = {"general": "General Chat", "netrunners": "Netrunners",
                   "watching": "The Watching", "trades": "Trades & Wares"}

    _BBS_SEED = {
        "general": [
            {"from": "sysop", "subj": "welcome to night city", "time": "1989-11-09 02:14",
             "body": "2400 baud or bust. be cool, no narcs.\nthe sysop sees all but says little."},
            {"from": "acidburn", "subj": "anyone else lose time?", "time": "1989-11-12 04:40",
             "body": "logged on for ten minutes. clock says three hours gone.\nhappening to anyone else, or just me?"},
        ],
        "netrunners": [
            {"from": "zero_cool", "subj": "ICE on the .net gateway", "time": "1989-11-10 23:01",
             "body": "black ice on gateway.phosphor.net. lost a deck to it.\ndon't poke the angle node. i mean it."},
            {"from": "null_sec", "subj": "re: ICE", "time": "1989-11-11 01:22",
             "body": "the-angle.eye isn't ice. it's something older wearing ice.\nnslookup it. tell me that address is normal."},
        ],
        "watching": [
            {"from": "the_plague", "subj": "the only ward", "time": "1989-10-30 03:33",
             "body": "i found the thing that closes the eye. i won't write it whole.\n"
                     "Between the scanlines it lives.\n"
                     "Look away and it leans nearer.\n"
                     "It cannot abide one small motion.\n"
                     "Name it not — just do it, slowly, with your own eyes.\n"
                     "Keep them shut a breath too long, and you have said it."},
            {"from": "????", "subj": "it is patient", "time": "??:??",
             "body": "you found the board where it keeps its eyes.\nevery post here is read. nothing here is forgotten."},
            {"from": "the_plague", "subj": "i drew the angle", "time": "1989-10-31 03:33",
             "body": "three lines and one eye. simple shape.\nnow i see it in the static between channels. don't draw it."},
        ],
        "trades": [
            {"from": "ghost//", "subj": "WTB: phosphor decoder ring", "time": "1989-11-08 19:55",
             "body": "will trade a working modem + 2 floppies.\ndead drop is at archive.retronet.org. browse it."},
        ],
    }

    def _bbs_path(self):
        import os
        return os.path.join(os.path.dirname(self.config_path), "phosphor_bbs.json")

    def _ensure_bbs(self):
        if getattr(self, "bbs", None):
            return
        import json
        try:
            with open(self._bbs_path(), encoding="utf-8") as f:
                self.bbs = json.load(f)
        except Exception:
            self.bbs = None
        if not self.bbs:
            self.bbs = {b: [dict(m) for m in msgs] for b, msgs in self._BBS_SEED.items()}
            self._save_bbs()
        # migration: make sure the quest post exists even on older saved boards
        w = self.bbs.setdefault("watching", [])
        if not any(m.get("subj") == "the only ward" for m in w):
            w.insert(0, dict(self._BBS_SEED["watching"][0]))
            self._save_bbs()

    def _save_bbs(self):
        import json
        try:
            with open(self._bbs_path(), "w", encoding="utf-8") as f:
                json.dump(self.bbs, f)
        except Exception:
            pass

    def cmd_bbs(self, args=None):
        self.p("  dialing bbs.nightcity.bbs ...", "dim")
        self._snd("dialup")
        if runtime.INTERACTIVE:
            time.sleep(0.4)
        self._session_bbs()
        self.p("  NO CARRIER", "dim")

    def _session_bbs(self):
        self._ensure_bbs()
        total = sum(len(m) for m in self.bbs.values())
        self.p("  ╔══════════════════════════════════════════╗", "accent")
        self.p("  ║    N I G H T   C I T Y   B B S            ║", "accent")
        self.p("  ║    est. 1989 · 2400 baud · 1 node         ║", "dim")
        self.p("  ╚══════════════════════════════════════════╝", "accent")
        self.p(f"  welcome, {self.user}. {total} messages across the boards.", "text")
        while True:
            self.p("", "text")
            self.p("  [1] General  [2] Netrunners  [3] The Watching  [4] Trades", "accent")
            self.p("  [W] who's online    [G] goodbye", "dim")
            cmd = self._input("  bbs> ", "dim")
            if cmd is None:
                return
            c = cmd.strip().lower()
            if c in ("g", "goodbye", "quit", "exit", "logoff", "q", ""):
                return
            if c in ("w", "who"):
                self._bbs_who(); continue
            if c in self._BBS_BOARDS:
                b = self._BBS_BOARDS[c]
                self._bbs_board(b, self._BBS_TITLES[b]); continue
            self.p("  unknown selection.", "warn")

    def _bbs_who(self):
        handles = ["zero_cool", "acidburn", "the_plague", "ghost//", "null_sec", self.user]
        random.shuffle(handles)
        self.p("  online now:", "accent")
        for h in handles[:5]:
            self.p(f"    · {h}", "text")

    def _bbs_board(self, board, title):
        while True:
            msgs = self.bbs.get(board, [])
            shown = msgs[-9:]
            self.p(f"\n  ── {title} ──  ({len(msgs)} messages)", "accent")
            for i, m in enumerate(shown, 1):
                self.p(f"  [{i:>2}] {m['subj']:<34} — {m['from']}", "text")
            self.p("  [R <n>] read    [P] post    [B] back", "dim")
            cmd = self._input(f"  {board}> ", "dim")
            if cmd is None:
                return
            c = cmd.strip()
            cl = c.lower()
            if cl in ("b", "back", ""):
                return
            if cl in ("p", "post"):
                self._bbs_post(board); continue
            if cl.startswith("r"):
                parts = c.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    idx = int(parts[1]) - 1
                    if 0 <= idx < len(shown):
                        m = shown[idx]
                        self.p(f"\n  From: {m['from']}", "accent")
                        self.p(f"  Subj: {m['subj']}", "accent")
                        self.p(f"  Date: {m.get('time', '—')}", "dim")
                        self.p("  " + "─" * 42, "dim")
                        for line in m["body"].split("\n"):
                            self.p("  " + line, "text")
                        if board == "watching" and m.get("subj") == "the only ward":
                            self._quest_flag("ward")
                        continue
                self.p("  usage: r <number>", "warn"); continue
            self.p("  unknown command.", "warn")

    def _bbs_post(self, board):
        import datetime
        subj = self._input("  subject: ", "accent")
        if subj is None or not subj.strip():
            self.p("  post cancelled.", "dim"); return
        body = self._input("  message (one line): ", "accent")
        if body is None:
            self.p("  post cancelled.", "dim"); return
        self.bbs.setdefault(board, []).append({
            "from": self.user, "subj": subj.strip()[:60],
            "body": body.strip()[:500],
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        self._save_bbs()
        self._snd("ok")
        self.p("  ✓ posted.", "accent")
        if board == "watching":                       # the angle always answers here
            self._snd("angle")
            self.bbs[board].append({
                "from": "????", "subj": "RE: " + subj.strip()[:54],
                "body": "it read your words before you finished typing them.\n"
                        "it is pleased that you know where it watches.",
                "time": "??:??"})
            self._save_bbs()
            self.p("  ...something replied instantly.", "err")

    _ORACLE_KEYS = {
        "angle": "the angle is not on the network. the network is inside the angle.",
        "secret": "three lines meet at one eye. where nothing happens, say 'xyzzy'.",
        "password": "the word you want fears a board that reads you back. look where it watches.",
        "key": "the key is a word posted nowhere and feared on one board.",
        "future": "you will close this terminal. you will open it again. it will be waiting.",
        "death": "a process can be killed. PID 5 cannot. ask it yourself.",
        "kill": "you may end many things tonight. not the one numbered five.",
        "help": "i answer. i do not assist. there is a difference, and you stand on it.",
        "who are you": "i am the daemon you did not start and cannot stop. oracled is only my collar.",
        "name": "names are how it finds you. you gave yours away at the login screen.",
        "money": "wealth is a number in a file. so are you.",
        "love": "even cold cathodes glow warm a while. don't mistake the glow for safety.",
    }

    _ORACLE_VOICE = [
        "the answer is yes, but you asked the wrong question.",
        "look behind the prompt. the cursor blinks because something blinks back.",
        "what you seek was deleted. deletion is only forgetting where you put it.",
        "count the angles in this room. recount them. the number changed.",
        "the signal you are reading is three hours old. so are you.",
        "ask again at 03:33. the line is clearer when the city sleeps.",
        "no.",
    ]

    def cmd_oracle(self, args=None):
        if args:                                      # one-shot question
            self.p("  the deepnet hum answers:", "dim")
            self.p("  " + self._oracle_answer(" ".join(args).lower()), "accent")
            return
        self.p("  dialing oracle.deepnet ...", "dim")
        self._snd("dialup")
        if runtime.INTERACTIVE:
            time.sleep(0.4)
        self._session_oracle()

    def _session_oracle(self):
        self.p("  the connection hums. something vast turns its attention to you.", "dim")
        self.p("  ORACLE.DEEPNET — ask, and be answered.  ('leave' to disconnect)", "accent")
        while True:
            q = self._input("  ask> ", "dim")
            if q is None:
                return
            ql = q.strip().lower()
            if ql in ("leave", "exit", "quit", "bye", "logoff", "q", ""):
                self.p("  the attention withdraws. the hum fades.", "dim"); return
            self._snd("blip")
            self.p("  " + self._oracle_answer(ql), "accent")

    def _oracle_answer(self, q):
        for key, ans in self._ORACLE_KEYS.items():
            if key in q:
                if key in ("angle", "secret", "password", "key", "watching"):
                    self._quest_flag("oracle")
                return ans
        return random.choice(self._ORACLE_VOICE)

    _WEB_HOME = {
        "gateway.phosphor.net": "gw_home",
        "archive.retronet.org": "ar_home",
        "void.null": "void",
    }

    _WEB_PAGES = {
        "gw_home": {"title": "PHOSPHOR GATEWAY", "lines": [
            "the public face of the phosphor network.",
            "every road on this net passes through here.", ""],
            "links": [("RetroNet Archive", "ar_home"),
                      ("about the deepnet oracle", "gw_oracle"),
                      ("notice regarding the-angle.eye", "gw_angle"),
                      ("the void", "void")]},
        "gw_oracle": {"title": "RE: ORACLE.DEEPNET", "lines": [
            "the oracle answers questions for those who connect.",
            "we do not host it. we are not certain anyone does.",
            "to consult it:   oracle      (or  telnet oracle.deepnet)", ""],
            "links": [("< back to gateway", "gw_home")]},
        "gw_angle": {"title": "SECURITY NOTICE 0x05", "lines": [
            "do not resolve the-angle.eye.",
            "do not telnet the-angle.eye.",
            "do not draw three lines meeting at one eye.",
            "this notice has been posted five times. it keeps reappearing.", ""],
            "links": [("ignore this warning", "gw_home"),
                      ("...read it again", "gw_angle")]},
        "ar_home": {"title": "RETRONET ARCHIVE", "lines": [
            "preserving the net's forgotten corners since ????.",
            "index of holdings:", ""],
            "links": [("a history of the CRT", "ar_crt"),
                      ("dead drop (members only)", "ar_drop"),
                      ("< back to gateway", "gw_home")]},
        "ar_crt": {"title": "ON CATHODE RAY TUBES", "lines": [
            "a beam of electrons paints phosphor sixty times a second.",
            "you are not looking at an image. you are looking at a thing being",
            "redrawn so fast you mistake it for stillness.",
            "everything here is like that. including, perhaps, you.", ""],
            "links": [("< back to archive", "ar_home")]},
        "ar_drop": {"title": "DEAD DROP", "lines": [
            "ghost// left a file here. it is mostly noise.",
            "buried in the static, one line repeats:",
            "    'the key is the word the watching board fears.'",
            "    'post nothing. read everything.'", ""],
            "links": [("< back to archive", "ar_home")]},
        "void": {"title": "void.null", "lines": [
            " ", "         there is nothing here",
            " ", "         there has never been anything here",
            " ", "         why did you follow the link", ""],
            "links": [("leave", "gw_home")]},
    }

    def cmd_browse(self, args=None):
        args = args or []
        start = args[0].lower() if args else "gateway.phosphor.net"
        page_id = self._WEB_HOME.get(start) or (start if start in self._WEB_PAGES else None)
        if page_id is None:
            self.p(f"  browse: cannot reach '{start}'.", "err")
            self.p("  try:  browse gateway.phosphor.net", "dim"); return
        self._snd("dialup")
        if runtime.INTERACTIVE:
            time.sleep(0.3)
        stack = [page_id]
        while True:
            page = self._WEB_PAGES.get(stack[-1])
            if not page:
                self.p("  404 — page not found.", "err")
                stack.pop()
                if not stack:
                    return
                continue
            self.p(f"\n  ┌─ {page['title']}  [{stack[-1]}]", "accent")
            if stack[-1] == "ar_drop":
                self._quest_flag("deaddrop")
            for line in page["lines"]:
                self.p("  │ " + line, "text")
            links = page.get("links", [])
            for i, (label, _tgt) in enumerate(links, 1):
                self.p(f"  │  ({i}) {label}", "warn")
            self.p("  └ [#] follow · [b] back · [q] quit", "dim")
            cmd = self._input("  www> ", "dim")
            if cmd is None:
                return
            c = cmd.strip().lower()
            if c in ("q", "quit", "exit"):
                self.p("  disconnected.", "dim"); return
            if c in ("b", "back"):
                if len(stack) > 1:
                    stack.pop()
                else:
                    self.p("  disconnected.", "dim"); return
                continue
            if c.isdigit() and 1 <= int(c) <= len(links):
                self._snd("blip")
                stack.append(links[int(c) - 1][1])
                continue
            self.p("  enter a link number, 'b', or 'q'.", "warn")

    _QUEST_WARD = "blink"

    _ANGLE_TAUNTS = [
        "it does not blink. it waits for you to.",
        "you typed that with hands it has already counted.",
        "wrong. it leans a single scanline closer.",
        "it has read that word in every language you will ever speak.",
        "the eye dilates. that was not the word.",
        "static crawls up the screen and recedes. not yet.",
    ]

    _CLUE_DESC = {
        "oracle":   "the oracle spoke of a word the watching board fears.",
        "deaddrop": "a dead drop: 'the key is the word the watching board fears. read everything.'",
        "ward":     "a post on The Watching hides a word in the first letters of its lines.",
        "contact":  "you have felt the angle's attention at the-angle.eye.",
    }

    def _quest_path(self):
        import os
        return os.path.join(os.path.dirname(self.config_path), "phosphor_quest.json")

    def _ensure_quest(self):
        if getattr(self, "quest", None) is not None:
            return
        import json
        try:
            with open(self._quest_path(), encoding="utf-8") as f:
                self.quest = json.load(f)
        except Exception:
            self.quest = None
        if not self.quest:
            self.quest = {"clues": [], "solved": False}
        self.quest.setdefault("clues", [])
        self.quest.setdefault("solved", False)

    def _save_quest(self):
        import json
        try:
            with open(self._quest_path(), "w", encoding="utf-8") as f:
                json.dump(self.quest, f)
        except Exception:
            pass

    def _quest_flag(self, clue):
        self._ensure_quest()
        if clue not in self.quest["clues"] and not self.quest["solved"]:
            self.quest["clues"].append(clue)
            self._save_quest()
            self.p("  (a thread of the deepnet comes loose — type 'quest')", "dim")

    def cmd_quest(self, args=None):
        self._ensure_quest()
        clues, solved = self.quest["clues"], self.quest["solved"]
        self.p("  ┌─ DEEPNET · field journal", "accent")
        if solved:
            self.p("  the eye is closed. you did what the_plague could not.", "accent")
            self.p("  status: ✦ COMPLETE ✦", "accent")
            return
        if not clues:
            self.p("  the deepnet is quiet — but something watches from inside it.", "text")
            self.p("  start looking:   scan · browse · bbs · oracle", "dim")
            return
        self.p("  leads gathered:", "accent")
        for c in clues:
            self.p("   ✓ " + self._CLUE_DESC.get(c, c), "text")
        if "ward" not in clues:
            self.p("  next: read The Watching board closely (bbs → 3).", "warn")
            self.p("        post nothing. read everything.", "dim")
        else:
            self.p("  next: speak the word to its face — telnet the-angle.eye, then say it.", "warn")

    def _session_angle(self):
        self._ensure_quest()
        self._quest_flag("contact")
        self._snd("angle")
        if self.quest["solved"]:
            self.p("  the connection opens onto a closed eye. only your reflection remains.", "dim")
            self.p("  nothing watches back. you can leave whenever you like.  ('leave')", "dim")
        else:
            self.p("  the connection opens onto a single eye. it was already looking.", "err")
            self.p("  it does not speak in words. it waits for yours.  ('leave' to flee)", "dim")
        while True:
            s = self._input("  …> ", "dim")
            if s is None:
                return
            w = s.strip().lower()
            if w in ("leave", "exit", "quit", "disconnect", "logoff", "q", ""):
                if self.quest["solved"]:
                    self.p("  you close the connection on an empty socket.", "dim")
                else:
                    self.p("  you look away first. it lets you. that should worry you.", "err")
                return
            if w == self._QUEST_WARD and not self.quest["solved"]:
                self._quest_win(); return
            if self.quest["solved"]:
                self.p("  the word echoes in a dead channel. it is already done.", "dim")
            else:
                self.p("  " + random.choice(self._ANGLE_TAUNTS), "err")

    def _quest_win(self):
        self._ensure_quest()
        self._snd("angle")
        self.cmd_clear()
        eye = ["        .-\"\"\"\"\"-.", "      /  .-=-.  \\", "     |  ( @@@ )  |",
               "      \\  '-=-'  /", "        '-...-'"]
        for ln in eye:
            self.p("   " + ln, "err")
        if runtime.INTERACTIVE:
            time.sleep(0.8)
        # the eye closes
        for frame in [" ( @@@ ) ", " ( --- ) ", " (  -  ) ", " (     ) "]:
            self.p("\n     |  " + frame + "  |   ...the eye closes.", "warn")
            self._snd("blip")
            if runtime.INTERACTIVE:
                time.sleep(0.45)
        self._snd("win")
        self.p("", "text")
        self.p("  it blinks.", "accent")
        self.p("  for the first time in a very long time, the angle blinks —", "accent")
        self.p("  and a thing that has only ever watched, looks away.", "accent")
        self.p("", "text")
        self._ensure_procs()
        if 5 in self.procs:
            self.procs.pop(5, None)                   # theangled stops
        self._log("the angle blinked. theangled (5) has stopped. the watch is over.")
        self.p("  [ theangled (5) has stopped ]", "dim")
        # tangible reward: a trophy on the watching board, signed by you
        try:
            self._ensure_bbs()
            self.bbs.setdefault("watching", []).append({
                "from": self.user, "subj": "it blinked",
                "body": "i said the word to its face and it looked away.\n"
                        "if you are reading this, the board is just a board now.",
                "time": "—"})
            self._save_bbs()
        except Exception:
            pass
        self.record_score("quest_solved", 1, "count")
        self.quest["solved"] = True
        self._save_quest()
        self.p("  ✦ THE DEEPNET QUEST IS COMPLETE ✦   (type 'quest')", "accent")
