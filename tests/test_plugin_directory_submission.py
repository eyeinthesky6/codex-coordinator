from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class PluginDirectorySubmissionTests(unittest.TestCase):
    def test_manifest_has_public_listing_metadata(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["author"]["url"], "https://github.com/eyeinthesky6")
        self.assertEqual(
            manifest["homepage"], "https://eyeinthesky6.github.io/codex-coordinator/"
        )
        self.assertEqual(
            manifest["repository"], "https://github.com/eyeinthesky6/codex-coordinator"
        )
        interface = manifest["interface"]
        self.assertEqual(interface["websiteURL"], manifest["homepage"])
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        self.assertEqual(
            interface["supportURL"],
            "https://github.com/eyeinthesky6/codex-coordinator/blob/main/SUPPORT.md",
        )
        self.assertEqual(
            interface["privacyPolicyURL"],
            "https://github.com/eyeinthesky6/codex-coordinator/blob/main/PRIVACY.md",
        )
        self.assertEqual(
            interface["termsOfServiceURL"],
            "https://github.com/eyeinthesky6/codex-coordinator/blob/main/TERMS.md",
        )
        self.assertEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))

    def test_public_legal_documents_describe_actual_local_boundaries(self) -> None:
        privacy = (REPOSITORY / "PRIVACY.md").read_text(encoding="utf-8")
        terms = (REPOSITORY / "TERMS.md").read_text(encoding="utf-8")

        self.assertIn("no publisher-operated server", privacy)
        self.assertIn("does not read or store prompts", privacy)
        self.assertIn("Native Codex remains responsible for task transcripts", privacy)
        self.assertIn("never imported or started by the base runtime", privacy)
        self.assertIn("remain only in the user's local project until", privacy)
        self.assertIn("https://openai.com/policies/privacy-policy/", privacy)
        self.assertIn("MIT License", terms)
        self.assertIn("does not replace human review", terms)
        self.assertIn("https://openai.com/policies/terms-of-use/", terms)

    def test_public_site_links_the_legal_documents(self) -> None:
        page = (REPOSITORY / "site" / "index.html").read_text(encoding="utf-8")

        self.assertIn("blob/main/PRIVACY.md", page)
        self.assertIn("blob/main/TERMS.md", page)


if __name__ == "__main__":
    unittest.main()
