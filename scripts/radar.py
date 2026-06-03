#!/usr/bin/env python3
"""
Claude Release Radar — engine.

A dependency-free (Python stdlib only) engine that aggregates official Claude
release sources, diffs them against a saved "last seen" state, inspects the
local environment, and prints a personalized briefing of *only what's new*.

Design goals
------------
- No third-party packages. Runs anywhere Python 3.8+ runs.
- Never crash on a bad network / bad page: every fetch and parse is best-effort.
- Two fetch modes:
    1. self-fetch via urllib (convenient, needs network)
    2. --input DIR : read pre-fetched raw files named "<source_id>.raw"
       (so the calling agent can fetch with its own WebFetch tool and feed them in)
- Deterministic where feeds are structured (npm, Atom/RSS, CHANGELOG.md).
  Narrative pages (HTML release notes, news) are marked type "agent" and handed
  back to the orchestrating agent to summarize — the engine does not scrape them.

Commands
--------
  radar.py check     # aggregate + diff + personalize + render
  radar.py env       # just the detected local environment
  radar.py sources   # list configured sources
  radar.py mark-seen # mark everything currently known as seen (commit baseline)

See `reference/sources.md` for the source registry and how to extend it.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from xml.etree import ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCES = os.path.join(SCRIPT_DIR, "sources.json")
USER_AGENT = "claude-release-radar/1.0 (+https://github.com/)"
SEEN_CAP = 250  # cap stored ids per source so state.json never grows unbounded


# --------------------------------------------------------------------------- #
# Paths / state
# --------------------------------------------------------------------------- #
def state_path(override: str | None = None) -> str:
    if override:
        return os.path.expanduser(override)
    env = os.environ.get("CLR_STATE")
    if env:
        return os.path.expanduser(env)
    base = os.path.join(os.path.expanduser("~"), ".claude", "claude-release-radar")
    return os.path.join(base, "state.json")


def load_state(path: str) -> tuple[dict, bool]:
    """Return (state, existed)."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), True
        except Exception:
            pass
    return {"last_checked": None, "seen": {}, "versions": {}}, False


def save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


# --------------------------------------------------------------------------- #
# Networking (best-effort)
# --------------------------------------------------------------------------- #
def http_get(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    except Exception:
        return None


def read_input_file(input_dir: str, source_id: str) -> str | None:
    for ext in (".raw", ".json", ".xml", ".md", ".txt", ""):
        p = os.path.join(input_dir, source_id + ext)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                return None
    return None


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = _TAG_RE.sub(" ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    text = _WS_RE.sub(" ", text)
    return text.strip()


def first_line(text: str, limit: int = 280) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    line = text.splitlines()[0].strip()
    return line[:limit] + ("…" if len(line) > limit else "")


def localname(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_iso(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    # Try a few common shapes; fall back to the raw string.
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return _dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    return m.group(0) if m else s


def item(source, category, _id, title, date=None, url=None, summary=""):
    return {
        "source": source,
        "category": category,
        "id": str(_id),
        "title": title.strip() if title else "(untitled)",
        "date": date,
        "url": url,
        "summary": (summary or "").strip(),
    }


# --------------------------------------------------------------------------- #
# Source parsers — each returns a list of normalized items
# --------------------------------------------------------------------------- #
def parse_npm(raw: str, src: dict) -> list[dict]:
    try:
        data = json.loads(raw)
    except Exception:
        return []
    version = data.get("version")
    if not version:
        return []
    desc = data.get("description", "")
    return [item(src["id"], src["category"], version,
                 f'{src["label"]} v{version}',
                 date=None, url=src.get("homepage") or src["url"],
                 summary=desc)]


def parse_feed(raw: str, src: dict) -> list[dict]:
    """Handle both Atom (<entry>) and RSS (<item>)."""
    try:
        root = ET.fromstring(raw.encode("utf-8") if isinstance(raw, str) else raw)
    except Exception:
        return []
    items = []
    nodes = [n for n in root.iter() if localname(n.tag) in ("entry", "item")]
    for n in nodes:
        title = link = date = ident = summary = None
        for child in n:
            ln = localname(child.tag)
            if ln == "title":
                title = (child.text or "").strip()
            elif ln == "link":
                link = child.get("href") or (child.text or "").strip() or link
            elif ln in ("updated", "published", "pubDate", "date"):
                date = date or parse_iso(child.text)
            elif ln in ("id", "guid"):
                ident = (child.text or "").strip()
            elif ln in ("summary", "content", "description"):
                summary = summary or strip_html(child.text or "")
        ident = ident or link or title
        if not ident:
            continue
        items.append(item(src["id"], src["category"], ident, title or ident,
                          date=date, url=link, summary=first_line(summary or "")))
    return items


_VER_HEADER_RE = re.compile(r"^#{1,3}\s*\[?v?(\d+\.\d+(?:\.\d+)?[^\]\s]*)\]?", re.M)


def parse_markdown_changelog(raw: str, src: dict) -> list[dict]:
    """Split a CHANGELOG.md into per-version blocks keyed by version header."""
    matches = list(_VER_HEADER_RE.finditer(raw))
    items = []
    for i, m in enumerate(matches):
        version = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        # Pull the first few bullet lines as a teaser.
        bullets = [ln.strip("-*• \t") for ln in body.splitlines()
                   if ln.strip().startswith(("-", "*", "•"))]
        teaser = "; ".join(b for b in bullets[:4] if b)
        items.append(item(src["id"], src["category"], version,
                          f'{src["label"]} v{version}',
                          date=None, url=src.get("homepage") or src["url"],
                          summary=teaser or first_line(body)))
    return items


PARSERS = {
    "npm": parse_npm,
    "atom": parse_feed,
    "rss": parse_feed,
    "feed": parse_feed,
    "markdown-changelog": parse_markdown_changelog,
}


# --------------------------------------------------------------------------- #
# Environment detection (best-effort, never raises)
# --------------------------------------------------------------------------- #
def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def detect_cli_version() -> str | None:
    for cmd in (["claude", "--version"], ["claude-code", "--version"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            text = (out.stdout or "") + (out.stderr or "")
            m = re.search(r"(\d+\.\d+\.\d+)", text)
            if m:
                return m.group(1)
        except Exception:
            continue
    return None


def _list_skill_dirs(root: str) -> list[str]:
    found = []
    if not os.path.isdir(root):
        return found
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "SKILL.md")):
            found.append(name)
    return found


def detect_skills() -> list[str]:
    roots = [
        os.path.expanduser("~/.claude/skills"),
        os.path.join(os.getcwd(), ".claude", "skills"),
    ]
    out = []
    for r in roots:
        out.extend(_list_skill_dirs(r))
    return sorted(set(out))


def detect_plugins() -> list[str]:
    root = os.path.expanduser("~/.claude/plugins")
    out = []
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            if name.startswith("."):
                continue
            if os.path.isdir(os.path.join(root, name)):
                out.append(name)
    return out


def detect_mcp_servers() -> list[str]:
    """Collect MCP server *names* only — never values, to avoid leaking secrets."""
    names: set[str] = set()
    candidates = [
        os.path.expanduser("~/.claude.json"),
        os.path.join(os.getcwd(), ".mcp.json"),
        os.path.join(os.getcwd(), ".claude", "settings.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for block in (data, data.get("projects", {}).get(os.getcwd(), {}) if isinstance(data, dict) else {}):
            if isinstance(block, dict) and isinstance(block.get("mcpServers"), dict):
                names.update(block["mcpServers"].keys())
    return sorted(names)


def detect_env() -> dict:
    return {
        "cli_version": _safe(detect_cli_version, None),
        "skills": _safe(detect_skills, []),
        "plugins": _safe(detect_plugins, []),
        "mcp_servers": _safe(detect_mcp_servers, []),
        "platform": sys.platform,
        "cwd": os.getcwd(),
    }


# --------------------------------------------------------------------------- #
# Version comparison & impact correlation
# --------------------------------------------------------------------------- #
def _vt(v: str) -> tuple:
    parts = re.findall(r"\d+", v or "")
    return tuple(int(p) for p in parts[:3]) or (0,)


FEATURE_HINTS = {
    "hook": "Hooks let you run shell commands on Claude Code lifecycle events — see `/hooks`.",
    "slash command": "Custom slash commands live in `.claude/commands/` — try defining one.",
    "subagent": "Subagents parallelize work — try delegating a task with the Task tool.",
    "mcp": "New MCP capability — review your connected servers with `/mcp`.",
    "skill": "Skills extend Claude with packaged know-how — manage them in `~/.claude/skills/`.",
    "plugin": "Plugins bundle skills/commands/MCP — browse with `/plugin`.",
    "model": "A model change may affect cost/quality — switch with `/model`.",
    "output style": "Output styles reshape responses — see `/output-style`.",
    "checkpoint": "Checkpointing lets you rewind sessions — try `/rewind`.",
}


def compute_impacts(new_items: list[dict], env: dict, npm_latest: str | None) -> dict:
    alerts: list[str] = []

    # 1) CLI version gap.
    installed = env.get("cli_version")
    if installed and npm_latest and _vt(npm_latest) > _vt(installed):
        alerts.append(
            f"You're running Claude Code v{installed}; latest is v{npm_latest}. "
            f"Update with `claude update` (or `npm i -g @anthropic-ai/claude-code`)."
        )

    # 2) Per-item personalization keyword set drawn from the user's actual setup.
    personal_keywords = set()
    for bucket in ("skills", "plugins", "mcp_servers"):
        for name in env.get(bucket, []):
            for token in re.split(r"[-_/\s]+", str(name).lower()):
                if len(token) >= 4:
                    personal_keywords.add(token)

    try_hints: list[str] = []
    for it in new_items:
        hay = (it.get("title", "") + " " + it.get("summary", "")).lower()
        tags = []
        hits = sorted(k for k in personal_keywords if k in hay)
        if hits:
            tags.append("affects your setup: " + ", ".join(hits[:3]))
        for feat, hint in FEATURE_HINTS.items():
            if feat in hay:
                tags.append(f"capability: {feat}")
                if hint not in try_hints:
                    try_hints.append(hint)
        it["impacts"] = tags

    return {"alerts": alerts, "try_hints": try_hints[:6]}


# --------------------------------------------------------------------------- #
# Core: aggregate + diff
# --------------------------------------------------------------------------- #
def load_sources(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [s for s in data.get("sources", []) if s.get("enabled", True)]


def aggregate(sources, input_dir, timeout):
    """Return (parsed_items, agent_sources, fetch_errors, npm_latest)."""
    parsed, agent_sources, errors = [], [], []
    npm_latest = None
    for src in sources:
        stype = src.get("type")
        if stype == "agent":
            agent_sources.append(src)
            continue
        raw = (read_input_file(input_dir, src["id"]) if input_dir
               else http_get(src["url"], timeout))
        if not raw:
            errors.append(src["id"])
            continue
        parser = PARSERS.get(stype)
        if not parser:
            errors.append(src["id"])
            continue
        items = parser(raw, src)
        if stype == "npm" and items:
            npm_latest = items[0]["id"]
        parsed.extend(items)
    return parsed, agent_sources, errors, npm_latest


def diff_new(parsed, state, first_run, baseline_limit):
    seen = state.get("seen", {})
    new = []
    for it in parsed:
        sid = it["source"]
        if it["id"] not in seen.get(sid, []):
            new.append(it)
    # Sort newest first where dates exist; undated items keep source order.
    new.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    if first_run and len(new) > baseline_limit:
        new = new[:baseline_limit]
    return new


def commit_state(state, parsed, npm_latest):
    seen = state.setdefault("seen", {})
    by_source: dict[str, list[str]] = {}
    for it in parsed:
        by_source.setdefault(it["source"], []).append(it["id"])
    for sid, ids in by_source.items():
        merged = ids + [x for x in seen.get(sid, []) if x not in ids]
        seen[sid] = merged[:SEEN_CAP]
    if npm_latest:
        state.setdefault("versions", {})["claude-code-npm"] = npm_latest
    state["last_checked"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return state


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _days_since(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        then = _dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = _dt.datetime.now(_dt.timezone.utc) - then
        d = delta.days
        return "today" if d <= 0 else ("1 day ago" if d == 1 else f"{d} days ago")
    except Exception:
        return iso


def render_markdown(result: dict) -> str:
    new = result["new_items"]
    env = result["env"]
    impacts = result["impacts"]
    today = _dt.date.today().isoformat()
    out = [f"# 🛰️ Claude Release Radar — {today}"]
    last = result["state_last_checked"]
    if result["first_run"]:
        out.append("_First run — establishing your baseline. Future checks show only what changed._\n")
    else:
        out.append(f"_Since you last checked: {_days_since(last)}._\n")

    if not new and not impacts["alerts"]:
        out.append("✅ **You're all caught up.** No new Claude releases since your last check.")
        return "\n".join(out)

    if impacts["alerts"]:
        out.append("## ⚠️ Affects your setup")
        for a in impacts["alerts"]:
            out.append(f"- {a}")
        out.append("")

    personal = [it for it in new if it.get("impacts")]
    if personal:
        out.append("## 🎯 Relevant to you")
        for it in personal:
            tags = "; ".join(it["impacts"])
            out.append(f"- **{it['title']}** — {tags}")
            if it.get("url"):
                out[-1] += f" · [details]({it['url']})"
        out.append("")

    if new:
        out.append("## 🆕 What's new")
        by_cat: dict[str, list[dict]] = {}
        for it in new:
            by_cat.setdefault(it["category"], []).append(it)
        for cat in sorted(by_cat):
            out.append(f"### {cat}")
            for it in by_cat[cat]:
                line = f"- **{it['title']}**"
                if it.get("date"):
                    line += f" ({it['date']})"
                if it.get("summary"):
                    line += f" — {it['summary']}"
                if it.get("url"):
                    line += f" · [link]({it['url']})"
                out.append(line)
            out.append("")

    if result["agent_sources"]:
        out.append("## 🔎 Check these narrative sources (agent: WebFetch + summarize new entries)")
        for s in result["agent_sources"]:
            out.append(f"- {s['label']} ({s['category']}): {s['url']}")
        out.append("")

    if impacts["try_hints"]:
        out.append("## 💡 Try this")
        for h in impacts["try_hints"]:
            out.append(f"- {h}")
        out.append("")

    if result["errors"]:
        out.append(f"_Note: couldn't fetch {', '.join(result['errors'])} this run "
                   f"(network or layout change). Re-run or have the agent WebFetch them._")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_check(args):
    sources = load_sources(args.sources)
    sp = state_path(args.state)
    state, existed = load_state(sp)
    first_run = not existed

    parsed, agent_sources, errors, npm_latest = aggregate(
        sources, args.input, args.timeout)
    env = detect_env() if not args.no_env else {}
    new_items = diff_new(parsed, state, first_run, args.baseline_limit)
    impacts = compute_impacts(new_items, env, npm_latest) if env else {"alerts": [], "try_hints": []}

    result = {
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "first_run": first_run,
        "state_last_checked": state.get("last_checked"),
        "new_items": new_items,
        "agent_sources": [{"id": s["id"], "label": s["label"],
                           "category": s["category"], "url": s["url"]}
                          for s in agent_sources],
        "errors": errors,
        "env": env,
        "impacts": impacts,
        "npm_latest": npm_latest,
        "counts": {"new": len(new_items), "parsed": len(parsed)},
    }

    if args.commit:
        commit_state(state, parsed, npm_latest)
        save_state(sp, state)
        result["committed"] = True

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_markdown(result))
    return 0


def cmd_env(args):
    env = detect_env()
    print(json.dumps(env, indent=2) if args.json else
          "\n".join(f"{k}: {v}" for k, v in env.items()))
    return 0


def cmd_sources(args):
    with open(args.sources, "r", encoding="utf-8") as f:
        data = json.load(f)
    for s in data.get("sources", []):
        flag = "on " if s.get("enabled", True) else "off"
        print(f"[{flag}] {s['id']:<28} {s['type']:<18} {s['category']:<14} {s['url']}")
    return 0


def cmd_mark_seen(args):
    sources = load_sources(args.sources)
    sp = state_path(args.state)
    state, _ = load_state(sp)
    parsed, _agent, _errors, npm_latest = aggregate(sources, args.input, args.timeout)
    commit_state(state, parsed, npm_latest)
    save_state(sp, state)
    print(f"Marked {len(parsed)} known items as seen. State: {sp}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="radar.py", description="Claude Release Radar engine")
    p.add_argument("--sources", default=DEFAULT_SOURCES, help="path to sources.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="aggregate + diff + personalize + render")
    c.add_argument("--state", default=None, help="path to state.json (default ~/.claude/...)")
    c.add_argument("--input", default=None, help="dir of pre-fetched <source_id>.raw files")
    c.add_argument("--json", action="store_true", help="emit machine JSON instead of markdown")
    c.add_argument("--commit", action="store_true", help="mark all current items as seen after running")
    c.add_argument("--no-env", action="store_true", help="skip local environment detection")
    c.add_argument("--baseline-limit", type=int, default=6, help="max items to show on first run")
    c.add_argument("--timeout", type=int, default=20)
    c.set_defaults(func=cmd_check)

    e = sub.add_parser("env", help="show detected local environment")
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_env)

    s = sub.add_parser("sources", help="list configured sources")
    s.set_defaults(func=cmd_sources)

    m = sub.add_parser("mark-seen", help="commit current items as a baseline")
    m.add_argument("--state", default=None)
    m.add_argument("--input", default=None)
    m.add_argument("--timeout", type=int, default=20)
    m.set_defaults(func=cmd_mark_seen)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
