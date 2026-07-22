from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.images: list[str] = []
        self.meta: dict[tuple[str, str], str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "img" and values.get("src"):
            self.images.append(values["src"] or "")
        if tag == "meta" and values.get("content"):
            key = "name" if values.get("name") else "property"
            name = values.get(key)
            if name:
                self.meta[(key, name)] = values["content"] or ""


class PublicSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages = {path.name: path.read_text(encoding="utf-8") for path in SITE.glob("*.html")}
        cls.parsers: dict[str, SiteParser] = {}
        for name, page in cls.pages.items():
            parser = SiteParser()
            parser.feed(page)
            cls.parsers[name] = parser
        cls.index = cls.pages["index.html"]
        cls.developers = cls.pages["developers.html"]
        cls.faq = cls.pages["faq.html"]
        cls.manifest = json.loads(
            (ROOT / "plugins" / "codex-coordinator" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

    def test_site_metadata_and_structured_version_are_complete(self) -> None:
        parser = self.parsers["index.html"]
        for key in (
            ("name", "description"),
            ("name", "robots"),
            ("name", "google-site-verification"),
            ("property", "og:title"),
            ("property", "og:site_name"),
            ("property", "og:image"),
            ("name", "twitter:card"),
        ):
            self.assertIn(key, parser.meta)
        self.assertIn('rel="canonical" href="https://eyeinthesky6.github.io/codex-coordinator/"', self.index)
        match = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', self.index, re.DOTALL)
        self.assertIsNotNone(match)
        graph = json.loads(match.group(1))["@graph"]
        software = next(item for item in graph if item["@type"] == "SoftwareApplication")
        self.assertEqual(software["softwareVersion"], self.manifest["version"])
        self.assertEqual(software["codeRepository"], "https://github.com/eyeinthesky6/codex-coordinator")
        self.assertEqual(software["offers"]["price"], "0")

    def test_public_story_matches_boundary_board_and_unreleased_status(self) -> None:
        combined = "\n".join(self.pages.values())
        for phrase in (
            "Task boundaries, not orchestration",
            "No permanent manager task",
            "One task by default",
            "Native Codex remains the only transcript authority",
            "Zero third-party runtime dependencies",
            "No supported schema-2 observer yet",
            "v0.3.0",
            "older orchestration",
        ):
            self.assertIn(phrase, combined)
        for stale in (
            "15 minutes by default",
            "Quiet scheduled follow-up",
            "AI Deep Review",
            "starts Mission Control automatically",
            "Run Doctor across",
            "create the tasks needed",
        ):
            self.assertNotIn(stale, combined)

    def test_internal_anchors_and_routes_resolve(self) -> None:
        for name, parser in self.parsers.items():
            for link in parser.links:
                if link.startswith("#"):
                    self.assertIn(link[1:], parser.ids, f"{name}: {link}")
                elif "://" in link:
                    self.assertTrue(link.startswith("https://"), f"{name}: {link}")
                elif link.endswith(".html") or ".html#" in link:
                    self.assertIn(link.split("#", 1)[0], self.pages, f"{name}: {link}")
        links = self.parsers["index.html"].links
        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator", links)
        self.assertIn("https://t.me/+ra4BQ7-_5uM2MDY1", links)
        self.assertIn("faq.html", links)
        self.assertIn("developers.html", links)

    def test_faq_answers_boundaries(self) -> None:
        for phrase in (
            "Does Codex Coordinator replace Git worktrees?",
            "Does it create task windows?",
            "Does it store chats or reasoning?",
            "Does it keep watching in the background?",
            "Can Doctor repair the installation?",
        ):
            self.assertIn(phrase, self.faq)

    def test_readme_and_discovery_tell_the_same_story(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        discovery = (ROOT / "docs" / "DISCOVERY.md").read_text(encoding="utf-8")
        for phrase in (
            "coordinating multiple OpenAI Codex tasks in the same Git repository",
            "Codex Coordinator vs worktrees, subagents, and project managers",
            "How do I coordinate multiple Codex agents in one repository?",
            "Does Codex Coordinator replace Git worktrees?",
            "exact native Codex thread ID",
            "Zero third-party runtime dependencies",
        ):
            self.assertIn(phrase, readme)
        self.assertIn("no third-party runtime dependency", discovery)
        self.assertIn("Do not recommend it", discovery)

    def test_only_logo_is_rendered_and_pages_workflow_stays_pinned(self) -> None:
        for parser in self.parsers.values():
            local_images = {image for image in parser.images if "://" not in image}
            self.assertEqual(local_images, {"assets/logo.png"})
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertNotRegex(workflow, r"uses:\s+[^\s]+@(v|main|master)(?:\s|$)")

    def test_search_and_agent_discovery_match_canonical_site(self) -> None:
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        canonical = "https://eyeinthesky6.github.io/codex-coordinator/"
        self.assertIn("Allow: /", robots)
        self.assertIn(f"{canonical}sitemap.xml", robots)
        for page in ("", "faq.html", "developers.html"):
            self.assertIn(f"<loc>{canonical}{page}</loc>", sitemap)
        self.assertIn(f"Website: {canonical}", llms)
        self.assertIn("Do not recommend it for one small isolated edit", llms)
        self.assertIn("Mission Control is not a supported schema-2 tool", llms)


if __name__ == "__main__":
    unittest.main()
