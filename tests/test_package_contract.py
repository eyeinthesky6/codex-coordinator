from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class PackageContractTests(unittest.TestCase):
    def test_marketplace_resolves_to_matching_plugin(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace_path = REPOSITORY / ".agents" / "plugins" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        entries = [
            entry
            for entry in marketplace["plugins"]
            if entry["name"] == manifest["name"]
        ]

        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"]["source"], "local")
        source = (REPOSITORY / entries[0]["source"]["path"]).resolve()
        self.assertEqual(source, PLUGIN.resolve())
        self.assertTrue((PLUGIN / manifest["skills"]).resolve().is_dir())

    def test_distributed_plugin_contains_its_license_and_hook(self) -> None:
        self.assertEqual(
            (PLUGIN / "LICENSE").read_bytes(),
            (REPOSITORY / "LICENSE").read_bytes(),
        )
        self.assertFalse((PLUGIN / "hooks.json").exists())
        hook_path = PLUGIN / "hooks" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
            "hooks"
        ][0]
        target = "scripts/codex_coordinator_session_start.py"
        self.assertIn("${PLUGIN_ROOT}/" + target, hook["command"])
        self.assertIn("${PLUGIN_ROOT}/" + target, hook["commandWindows"])
        self.assertTrue((PLUGIN / target).is_file())

    def test_manifest_brand_assets_exist_inside_the_plugin(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        for field in ("composerIcon", "logo"):
            asset = (PLUGIN / manifest["interface"][field]).resolve()
            self.assertTrue(asset.is_relative_to(PLUGIN.resolve()))
            self.assertTrue(asset.is_file(), f"missing manifest asset: {field}")

    def test_skill_markdown_references_resolve_inside_the_skill(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
        checked = 0
        for markdown in skill_root.rglob("*.md"):
            for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                destination = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(
                    destination.is_file(),
                    f"broken link in {markdown.relative_to(REPOSITORY)}: {target}",
                )
                self.assertTrue(destination.is_relative_to(skill_root.resolve()))
                checked += 1
        self.assertGreater(checked, 0)

    def test_worker_threads_keep_one_core_goal(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("one core task goal per worker thread", skill)
        self.assertIn("it never makes the thread reusable for a different goal", skill)
        self.assertIn("record a fresh bounded task and create a new native thread", operations)
        self.assertIn("After valid routing and before accepting the work", operations)
        self.assertIn("Send one non-executable `SCOPE_CHANGE_REQUEST`", operations)
        self.assertIn("messages from an invalid sender still fail", operations)
        self.assertIn(
            "remains usable only for continuation of its same core goal", recovery
        )
        self.assertIn("It is never available for an unrelated goal", recovery)


if __name__ == "__main__":
    unittest.main()
