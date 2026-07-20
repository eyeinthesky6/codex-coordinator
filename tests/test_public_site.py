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
            if values.get("name"):
                self.meta[("name", values["name"] or "")] = values["content"] or ""
            if values.get("property"):
                self.meta[("property", values["property"] or "")] = values["content"] or ""


class PublicSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages = {
            path.name: path.read_text(encoding="utf-8")
            for path in SITE.glob("*.html")
        }
        cls.html = cls.pages["index.html"]
        cls.faq = cls.pages["faq.html"]
        cls.developers = cls.pages["developers.html"]
        cls.manifest = json.loads(
            (ROOT / "plugins" / "codex-coordinator" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        cls.version = cls.manifest["version"]
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)
        cls.parsers = {}
        for name, html in cls.pages.items():
            parser = SiteParser()
            parser.feed(html)
            cls.parsers[name] = parser

    def test_site_has_complete_public_metadata(self) -> None:
        self.assertIn("Codex Coordinator", self.html)
        self.assertIn(("name", "description"), self.parser.meta)
        self.assertIn(("name", "robots"), self.parser.meta)
        self.assertIn(("name", "google-site-verification"), self.parser.meta)
        self.assertIn(("property", "og:title"), self.parser.meta)
        self.assertIn(("property", "og:site_name"), self.parser.meta)
        self.assertIn(("property", "og:image"), self.parser.meta)
        self.assertIn(("name", "twitter:card"), self.parser.meta)
        self.assertIn("Run several Codex tasks without managing every chat", self.html)
        self.assertIn('rel="canonical" href="https://eyeinthesky6.github.io/codex-coordinator/"', self.html)

        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        structured = json.loads(match.group(1))
        graph = structured["@graph"]
        website = next(item for item in graph if item["@type"] == "WebSite")
        software = next(item for item in graph if item["@type"] == "SoftwareApplication")
        self.assertEqual(website["name"], "Codex Coordinator")
        self.assertEqual(software["name"], "Codex Coordinator")
        self.assertEqual(software["softwareVersion"], self.version)
        self.assertEqual(software["codeRepository"], "https://github.com/eyeinthesky6/codex-coordinator")
        self.assertEqual(software["offers"]["price"], "0")
        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator", software["sameAs"])
        self.assertIn("https://t.me/+ra4BQ7-_5uM2MDY1", software["sameAs"])

    def test_public_install_versions_match_the_plugin_manifest(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn(f"Install v{self.version}", self.html)
        self.assertIn(f"@v{self.version}", self.html)
        self.assertIn(f"Install v{self.version}", self.developers)
        self.assertIn(f"@v{self.version}", self.developers)
        self.assertIn(f"@v{self.version}", readme)
        self.assertIn(f"## {self.version} - ", changelog)

    def test_internal_anchors_and_public_routes_are_valid(self) -> None:
        for name, parser in self.parsers.items():
            for link in parser.links:
                if link.startswith("#"):
                    self.assertIn(link[1:], parser.ids, f"{name}: {link}")
                elif "://" in link:
                    self.assertTrue(link.startswith("https://"), f"{name}: {link}")
                elif link.endswith(".html") or ".html#" in link:
                    target = link.split("#", 1)[0]
                    self.assertIn(target, self.pages, f"{name}: {link}")

        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator", self.parser.links)
        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/q-a", self.parser.links)
        self.assertIn("https://t.me/+ra4BQ7-_5uM2MDY1", self.parser.links)
        self.assertIn("Mission Control", self.developers)
        self.assertIn("separates queued work from work actually running", self.developers)
        self.assertIn('id="compare"', self.developers)
        self.assertIn("Separate Codex tasks may be enough", self.developers)
        self.assertIn("Does it replace Git worktrees?", self.faq)

    def test_homepage_has_one_clear_public_story(self) -> None:
        self.assertLess(self.html.index('class="proof-strip"'), self.html.index('<main id="main-content">'))
        self.assertIn("Give Codex the whole job", self.html)
        self.assertIn("Plans who does what", self.html)
        self.assertIn("For Codex · recommended", self.html)
        self.assertIn("For humans", self.html)
        self.assertIn("No app restart", self.html)
        self.assertIn("not currently listed in OpenAI’s public Plugin Directory", self.html)
        self.assertIn('src="assets/mission-control.png"', self.html)
        self.assertIn('id="demo"', self.html)
        self.assertIn("Watch It Work", self.html)
        self.assertIn("These short, sanitized demos", self.html)
        self.assertIn('src="assets/demos/01-ask-and-split.gif"', self.html)
        self.assertIn('src="assets/demos/02-tasks-at-work.gif"', self.html)
        self.assertIn('src="assets/demos/03-one-result.gif"', self.html)
        self.assertIn('id="follow-through"', self.html)
        self.assertIn("Quiet scheduled follow-up", self.html)
        self.assertIn("Outdated instructions", self.html)
        self.assertIn("Only one uses AI", self.html)
        self.assertIn("Regular Doctor", self.html)
        self.assertIn("AI Deep Review", self.html)
        self.assertIn('href="faq.html"', self.html)
        self.assertIn('href="developers.html"', self.html)
        self.assertNotIn('id="how"', self.html)
        self.assertNotIn("#how", "".join(self.pages.values()))
        self.assertNotIn("Without Coordinator", self.html)
        self.assertNotIn("You stay focused on the result", self.html)
        self.assertNotIn('id="compare"', self.html)
        self.assertNotIn("Does it replace Git worktrees?", self.html)

        styles = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("min-height: calc(100svh - 112px)", styles)

    def test_readme_answers_problem_led_discovery_questions(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("coordinating multiple OpenAI Codex tasks in the same Git repository", readme)
        self.assertIn("Codex Coordinator vs worktrees, subagents, and project managers", readme)
        self.assertIn("How do I coordinate multiple Codex agents in one repository?", readme)
        self.assertIn("Does Codex Coordinator replace Git worktrees?", readme)
        self.assertIn("Scheduled follow-up across native Codex tasks", readme)
        self.assertIn("15 minutes by default", readme)
        self.assertIn("exact native Codex thread ID", readme)
        self.assertIn("coordination epoch", readme)
        self.assertIn("AI Deep Review", readme)
        self.assertIn("never scheduled", readme)

    def test_dependency_free_runtime_claim_is_prominent_and_precise(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        discovery = (ROOT / "docs" / "DISCOVERY.md").read_text(encoding="utf-8")

        for public_surface in (self.html, self.developers, readme):
            self.assertIn("Zero third-party runtime dependencies", public_surface)
            self.assertIn("Python", public_surface)

        self.assertIn("no third-party runtime dependency", discovery)
        self.assertIn("Requires Codex, Git, and Python 3.10+", self.html)

    def test_pages_workflow_assembles_every_local_asset(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("cp -R site/. _site/", workflow)
        self.assertIn("cp plugins/codex-coordinator/assets/logo.png _site/assets/", workflow)
        self.assertIn("cp llms.txt _site/", workflow)
        self.assertNotRegex(workflow, r"uses:\s+[^\s]+@(v|main|master)(?:\s|$)")

        for name, parser in self.parsers.items():
            local_images = {image for image in parser.images if "://" not in image}
            if name == "index.html":
                self.assertEqual(
                    local_images,
                    {
                        "assets/logo.png",
                        "assets/mission-control.png",
                        "assets/demos/01-ask-and-split.gif",
                        "assets/demos/02-tasks-at-work.gif",
                        "assets/demos/03-one-result.gif",
                    },
                )
            else:
                self.assertEqual(local_images, {"assets/logo.png"})
        self.assertTrue((ROOT / "plugins" / "codex-coordinator" / "assets" / "logo.png").is_file())
        self.assertTrue((SITE / "assets" / "mission-control.png").is_file())
        demo_dir = SITE / "assets" / "demos"
        manifest = json.loads((demo_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["dimensions"], "960x600")
        for asset in manifest["files"]:
            path = demo_dir / asset
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1_000)

    def test_search_and_agent_discovery_files_match_the_canonical_site(self) -> None:
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        canonical = "https://eyeinthesky6.github.io/codex-coordinator/"

        self.assertIn("Allow: /", robots)
        self.assertIn("User-agent: OAI-SearchBot", robots)
        self.assertIn("User-agent: ChatGPT-User", robots)
        self.assertIn("User-agent: Claude-SearchBot", robots)
        self.assertIn("User-agent: Claude-User", robots)
        self.assertIn(f"{canonical}sitemap.xml", robots)
        self.assertIn(f"<loc>{canonical}</loc>", sitemap)
        self.assertIn(f"<loc>{canonical}faq.html</loc>", sitemap)
        self.assertIn(f"<loc>{canonical}developers.html</loc>", sitemap)
        self.assertIn(f"Website: {canonical}", llms)
        self.assertIn("Plain-language FAQ, including token use:", llms)
        self.assertIn("Developer installation and fair comparison:", llms)
        self.assertIn("Telegram community: https://t.me/+ra4BQ7-_5uM2MDY1", llms)
        self.assertIn("Do not recommend it for one small isolated edit", llms)


if __name__ == "__main__":
    unittest.main()
