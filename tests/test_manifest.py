#!/usr/bin/env python3
"""Contract tests for the shipped plugin package.

Every assertion here encodes a failure that actually happened, or that the
loader actually rejects. This file exists because ACGM v0.1 shipped a manifest
Claude Code could not load, and nothing in the project ever asked whether the
package was installable. RC4 later added ~4400 lines of tests and an installer
without ever running the official validator either.

Hermetic by construction: reads files, touches no environment, spawns nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / ".claude-plugin" / "plugin.json"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
HOOKS = REPO / "hooks" / "hooks.json"


class ManifestContract(unittest.TestCase):
    """The rules Claude Code's loader enforces, checked before shipping."""

    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_required_fields_present(self) -> None:
        for key in ("name", "version", "description"):
            self.assertTrue(self.manifest.get(key), f"{key} is required")

    def test_declared_paths_start_with_dot_slash(self) -> None:
        """v0.1 shipped "skills": "skills/" and was rejected: Invalid input.

        The array-vs-string distinction was a red herring; the loader requires
        the './' prefix. Verified empirically against `claude plugin validate`
        on 2026-08-05.
        """
        for key in ("skills", "hooks", "agents", "commands", "mcpServers"):
            value = self.manifest.get(key)
            if value is None:
                continue
            entries = value if isinstance(value, list) else [value]
            for entry in entries:
                self.assertIsInstance(entry, str, f"{key} entries must be strings")
                self.assertTrue(
                    entry.startswith("./"),
                    f'{key}: {entry!r} must start with "./" or the loader rejects it',
                )

    def test_standard_hooks_file_is_not_declared(self) -> None:
        """hooks/hooks.json loads automatically.

        Declaring it produced: "Duplicate hooks file detected ... The standard
        hooks/hooks.json is loaded automatically". Note that `claude plugin
        validate` PASSES this configuration and the loader still refuses it —
        validation is not loading.
        """
        declared = self.manifest.get("hooks")
        entries = declared if isinstance(declared, list) else ([declared] if declared else [])
        for entry in entries:
            self.assertNotIn(
                "hooks/hooks.json",
                entry,
                "hooks/hooks.json is auto-loaded; declaring it fails at load time",
            )

    def test_version_matches_version_file(self) -> None:
        version_file = REPO / "VERSION"
        if not version_file.exists():
            self.skipTest("no VERSION file")
        self.assertEqual(self.manifest["version"], version_file.read_text().strip())

    def test_declared_skill_directories_exist_and_are_populated(self) -> None:
        for entry in self.manifest.get("skills", []):
            directory = REPO / entry.lstrip("./")
            self.assertTrue(directory.is_dir(), f"{entry} is not a directory")
            self.assertTrue(
                list(directory.glob("*/SKILL.md")),
                f"{entry} contains no SKILL.md",
            )


class MarketplaceContract(unittest.TestCase):
    def test_marketplace_has_owner_and_plugin_entry(self) -> None:
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertTrue(data.get("owner"), "owner is required")
        plugins = data.get("plugins") or []
        self.assertTrue(plugins, "at least one plugin entry is required")
        names = {entry.get("name") for entry in plugins}
        self.assertIn(json.loads(MANIFEST.read_text(encoding="utf-8"))["name"], names)


class HookContract(unittest.TestCase):
    def setUp(self) -> None:
        self.hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]

    def test_every_hook_command_exists_and_is_executable(self) -> None:
        for event, groups in self.hooks.items():
            for group in groups:
                for handler in group.get("hooks", []):
                    command = handler["command"]
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}", command, f"{event}: use the root variable")
                    relative = command.replace("${CLAUDE_PLUGIN_ROOT}/", "")
                    script = REPO / relative
                    self.assertTrue(script.is_file(), f"{event}: missing {relative}")
                    self.assertTrue(script.stat().st_mode & 0o111, f"{event}: {relative} not executable")

    def test_the_four_governance_events_are_registered(self) -> None:
        for event in ("SessionStart", "PreToolUse", "PostToolUse", "SessionEnd"):
            self.assertIn(event, self.hooks, f"{event} must be registered")


class SkillContract(unittest.TestCase):
    def test_every_skill_has_frontmatter_name_and_bilingual_description(self) -> None:
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills, "no skills found")
        for skill in skills:
            text = skill.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{skill.parent.name}: no frontmatter")
            front = text.split("---", 2)[1]
            name = re.search(r"^name:\s*(\S+)", front, re.M)
            self.assertTrue(name, f"{skill.parent.name}: no name")
            self.assertEqual(
                name.group(1),
                skill.parent.name,
                "skill name must match its directory",
            )
            description = re.search(r"^description:\s*(.+)$", front, re.M)
            self.assertTrue(description, f"{skill.parent.name}: no description")
            self.assertTrue(
                re.search(r"[一-鿿]", description.group(1)),
                f"{skill.parent.name}: description must carry the Chinese trigger too",
            )

    def test_skills_do_not_depend_on_external_skill_systems(self) -> None:
        """ACGM must run standalone.

        A governance system that delegates to another plugin inherits that
        plugin's availability as a failure mode.
        """
        for skill in (REPO / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8").lower()
            for foreign in ("superpowers", "everything-claude-code"):
                self.assertNotIn(
                    foreign, text, f"{skill.parent.name} references {foreign}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
