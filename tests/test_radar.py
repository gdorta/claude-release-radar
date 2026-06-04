"""
Unit tests for the Claude Release Radar engine (scripts/radar.py).

Stdlib only — no pytest, no third-party deps — so they run anywhere the engine
runs (Python 3.8+). Run with:

    python3 -m unittest discover -s tests
    # or
    npm test
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import radar  # noqa: E402


SRC = {
    "id": "demo",
    "label": "Demo",
    "category": "Claude Code",
    "url": "https://example.com/feed",
    "homepage": "https://example.com",
}


class TestParsers(unittest.TestCase):
    def test_parse_npm(self):
        raw = json.dumps({"version": "2.4.2", "description": "the agentic CLI"})
        items = radar.parse_npm(raw, SRC)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "2.4.2")
        self.assertEqual(items[0]["title"], "Demo v2.4.2")
        self.assertEqual(items[0]["summary"], "the agentic CLI")

    def test_parse_npm_garbage_is_safe(self):
        self.assertEqual(radar.parse_npm("not json", SRC), [])
        self.assertEqual(radar.parse_npm(json.dumps({"no": "version"}), SRC), [])

    def test_parse_atom_namespaced(self):
        raw = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>v2.4.2</title>
            <link href="https://example.com/v2.4.2"/>
            <updated>2026-05-30T10:00:00Z</updated>
            <id>tag:example,2026:v2.4.2</id>
            <summary>checkpoint and rewind</summary>
          </entry>
        </feed>"""
        items = radar.parse_feed(raw, SRC)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["title"], "v2.4.2")
        self.assertEqual(it["url"], "https://example.com/v2.4.2")
        self.assertEqual(it["date"], "2026-05-30")
        self.assertEqual(it["id"], "tag:example,2026:v2.4.2")
        self.assertIn("checkpoint", it["summary"])

    def test_parse_rss_and_entity_decode(self):
        raw = """<rss version="2.0"><channel>
          <item>
            <title>Item One</title>
            <link>https://example.com/1</link>
            <pubDate>Mon, 30 May 2026 10:00:00 +0000</pubDate>
            <guid>guid-1</guid>
            <description>hello &amp; world</description>
          </item>
        </channel></rss>"""
        items = radar.parse_feed(raw, SRC)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["title"], "Item One")
        self.assertEqual(it["url"], "https://example.com/1")
        self.assertEqual(it["id"], "guid-1")
        self.assertEqual(it["date"], "2026-05-30")
        self.assertEqual(it["summary"], "hello & world")

    def test_parse_feed_garbage_is_safe(self):
        self.assertEqual(radar.parse_feed("<not xml", SRC), [])

    def test_parse_markdown_changelog(self):
        raw = (
            "# Changelog\n\n"
            "## [1.2.0] - 2026-01-02\n"
            "- Added A\n- Fixed B\n\n"
            "## v1.1.0\n"
            "- Initial release\n"
        )
        items = radar.parse_markdown_changelog(raw, SRC)
        self.assertEqual([it["id"] for it in items], ["1.2.0", "1.1.0"])
        self.assertEqual(items[0]["title"], "Demo v1.2.0")
        self.assertIn("Added A", items[0]["summary"])
        self.assertIn("Fixed B", items[0]["summary"])
        # The "# Changelog" header has no version and must not become an item.
        self.assertNotIn("Changelog", [it["id"] for it in items])


class TestHelpers(unittest.TestCase):
    def test_strip_html(self):
        out = radar.strip_html("<p>Hello <b>there</b> &amp; <script>x()</script>world</p>")
        self.assertEqual(out, "Hello there & world")

    def test_parse_iso_formats(self):
        self.assertEqual(radar.parse_iso("2026-05-30T10:00:00Z"), "2026-05-30")
        self.assertEqual(radar.parse_iso("2026-05-30"), "2026-05-30")
        self.assertEqual(radar.parse_iso("Mon, 30 May 2026 10:00:00 +0000"), "2026-05-30")
        self.assertIsNone(radar.parse_iso(None))

    def test_version_tuple_is_numeric_not_lexical(self):
        self.assertEqual(radar._vt("2.4.2"), (2, 4, 2))
        # 2.10.0 must sort ABOVE 2.9.0 (numeric), unlike string comparison.
        self.assertGreater(radar._vt("2.10.0"), radar._vt("2.9.0"))
        self.assertGreater(radar._vt("2.4.2"), radar._vt("2.1.160"))
        self.assertEqual(radar._vt(""), (0,))


class TestDiff(unittest.TestCase):
    def _items(self, *ids):
        return [radar.item("demo", "Claude Code", i, f"v{i}") for i in ids]

    def test_diff_only_returns_unseen(self):
        parsed = self._items("1", "2", "3")
        state = {"seen": {"demo": ["1"]}}
        new = radar.diff_new(parsed, state, first_run=False, baseline_limit=6)
        self.assertEqual({it["id"] for it in new}, {"2", "3"})

    def test_first_run_caps_to_baseline_limit(self):
        parsed = self._items(*[str(n) for n in range(10)])
        new = radar.diff_new(parsed, {"seen": {}}, first_run=True, baseline_limit=3)
        self.assertEqual(len(new), 3)

    def test_commit_state_records_seen_and_version(self):
        state = {}
        parsed = self._items("1", "2")
        radar.commit_state(state, parsed, npm_latest="2.4.2")
        self.assertEqual(set(state["seen"]["demo"]), {"1", "2"})
        self.assertEqual(state["versions"]["claude-code-npm"], "2.4.2")
        self.assertIsNotNone(state["last_checked"])

    def test_commit_state_caps_seen_ids(self):
        state = {"seen": {"demo": [str(n) for n in range(radar.SEEN_CAP)]}}
        parsed = self._items("new-1", "new-2")
        radar.commit_state(state, parsed, npm_latest=None)
        self.assertEqual(len(state["seen"]["demo"]), radar.SEEN_CAP)
        self.assertIn("new-1", state["seen"]["demo"])


class TestImpacts(unittest.TestCase):
    def test_version_gap_alert(self):
        env = {"cli_version": "2.1.160", "skills": [], "plugins": [], "mcp_servers": []}
        impacts = radar.compute_impacts([], env, npm_latest="2.4.2")
        self.assertEqual(len(impacts["alerts"]), 1)
        self.assertIn("2.1.160", impacts["alerts"][0])
        self.assertIn("2.4.2", impacts["alerts"][0])

    def test_no_alert_when_up_to_date(self):
        env = {"cli_version": "2.4.2", "skills": [], "plugins": [], "mcp_servers": []}
        self.assertEqual(radar.compute_impacts([], env, npm_latest="2.4.2")["alerts"], [])

    def test_personalization_tags_items_matching_user_setup(self):
        env = {"cli_version": None, "skills": ["terraform"], "plugins": [], "mcp_servers": []}
        items = [radar.item("demo", "Claude Code", "1", "New terraform helper landed")]
        radar.compute_impacts(items, env, npm_latest=None)
        self.assertTrue(any("affects your setup" in t for t in items[0]["impacts"]))

    def test_feature_hint_surfaces_try_this(self):
        env = {"cli_version": None, "skills": [], "plugins": [], "mcp_servers": []}
        items = [radar.item("demo", "Claude Code", "1", "Added /hooks lifecycle support")]
        impacts = radar.compute_impacts(items, env, npm_latest=None)
        self.assertTrue(any("capability: hook" in t for t in items[0]["impacts"]))
        self.assertTrue(impacts["try_hints"])


class TestRender(unittest.TestCase):
    def _result(self, **over):
        base = {
            "first_run": False,
            "state_last_checked": "2026-05-25T00:00:00+00:00",
            "new_items": [],
            "agent_sources": [],
            "errors": [],
            "env": {},
            "impacts": {"alerts": [], "try_hints": []},
        }
        base.update(over)
        return base

    def test_render_all_caught_up(self):
        out = radar.render_markdown(self._result())
        self.assertIn("all caught up", out.lower())

    def test_render_populated_briefing(self):
        out = radar.render_markdown(self._result(
            new_items=[radar.item("demo", "Claude Code", "1", "v2.4.2", date="2026-05-30",
                                   url="https://example.com", summary="checkpoint/rewind")],
            impacts={"alerts": ["You're behind."], "try_hints": ["Try /hooks."]},
        ))
        self.assertIn("⚠️ Affects your setup", out)
        self.assertIn("🆕 What's new", out)
        self.assertIn("### Claude Code", out)
        self.assertIn("💡 Try this", out)


class TestPrivacy(unittest.TestCase):
    def test_mcp_detection_returns_names_only_never_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {
                "mcpServers": {
                    "my-secret-server": {
                        "command": "run",
                        "env": {"API_TOKEN": "SUPERSECRETVALUE"},
                    }
                }
            }
            with open(os.path.join(d, ".mcp.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            cwd = os.getcwd()
            try:
                os.chdir(d)
                names = radar.detect_mcp_servers()
            finally:
                os.chdir(cwd)
        self.assertIn("my-secret-server", names)
        # The whole point: values/keys of the config must never leak out.
        joined = " ".join(names)
        self.assertNotIn("SUPERSECRETVALUE", joined)
        self.assertNotIn("API_TOKEN", joined)


class TestSourcesRegistry(unittest.TestCase):
    def test_shipped_sources_json_is_valid_and_filtered(self):
        path = os.path.join(os.path.dirname(__file__), "..", "scripts", "sources.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Every source declares the fields the engine relies on.
        for s in data["sources"]:
            for field in ("id", "label", "category", "type", "url"):
                self.assertIn(field, s, f"{s.get('id')} missing {field}")
            self.assertIn(s["type"], set(radar.PARSERS) | {"agent"})
        # load_sources drops disabled entries.
        enabled = radar.load_sources(path)
        self.assertTrue(all(s.get("enabled", True) for s in enabled))
        self.assertLess(len(enabled), len(data["sources"]))  # at least one ships disabled


if __name__ == "__main__":
    unittest.main()
