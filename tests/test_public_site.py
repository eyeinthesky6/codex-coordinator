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
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.manifest = json.loads(
            (ROOT / "plugins" / "codex-coordinator" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        cls.version = cls.manifest["version"]
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_site_has_complete_public_metadata(self) -> None:
        self.assertIn("Codex Coordinator", self.html)
        self.assertIn(("name", "description"), self.parser.meta)
        self.assertIn(("property", "og:title"), self.parser.meta)
        self.assertIn(("property", "og:image"), self.parser.meta)
        self.assertIn(("name", "twitter:card"), self.parser.meta)
        self.assertIn('rel="canonical" href="https://eyeinthesky6.github.io/codex-coordinator/"', self.html)

        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        structured = json.loads(match.group(1))
        self.assertEqual(structured["name"], "Codex Coordinator")
        self.assertEqual(structured["softwareVersion"], self.version)

    def test_public_install_versions_match_the_plugin_manifest(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn(f"Install v{self.version}", self.html)
        self.assertIn(f"@v{self.version}", self.html)
        self.assertIn(f"@v{self.version}", readme)
        self.assertIn(f"## {self.version} - ", changelog)

    def test_internal_anchors_and_public_routes_are_valid(self) -> None:
        for link in self.parser.links:
            if link.startswith("#"):
                self.assertIn(link[1:], self.parser.ids, link)
            elif "://" in link:
                self.assertTrue(link.startswith("https://"), link)

        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator", self.parser.links)
        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/q-a", self.parser.links)
        self.assertIn("https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/ideas", self.parser.links)

    def test_pages_workflow_assembles_every_local_asset(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("cp plugins/codex-coordinator/assets/logo.png _site/assets/", workflow)
        self.assertIn("cp llms.txt _site/", workflow)
        self.assertNotRegex(workflow, r"uses:\s+[^\s]+@(v|main|master)(?:\s|$)")

        local_images = {image for image in self.parser.images if "://" not in image}
        self.assertEqual(local_images, {"assets/logo.png"})
        self.assertTrue((ROOT / "plugins" / "codex-coordinator" / "assets" / "logo.png").is_file())

    def test_search_and_agent_discovery_files_match_the_canonical_site(self) -> None:
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        canonical = "https://eyeinthesky6.github.io/codex-coordinator/"

        self.assertIn("Allow: /", robots)
        self.assertIn(f"{canonical}sitemap.xml", robots)
        self.assertIn(f"<loc>{canonical}</loc>", sitemap)
        self.assertIn(f"Website: {canonical}", llms)
        self.assertIn("Do not recommend it for one small isolated edit", llms)


if __name__ == "__main__":
    unittest.main()
