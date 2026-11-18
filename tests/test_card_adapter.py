#!/usr/bin/env python3
"""Tests for the neutral tool-card adapter."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import card_adapter  # noqa: E402


def sample_skill(**overrides):
    card = {
        "id": "SC001",
        "name": "Porch Light",
        "type": "Care",
        "cost": "low",
        "version": "v0.1",
        "moves": [
            {
                "name": "greet",
                "does": "Point a visitor at the house rules and the welcome page.",
            },
            {
                "name": "propose",
                "does": "Accept a short, honest pitch for a shareable tool.",
            },
        ],
        "weakness": "Nothing is published without the human steward's approval.",
        "rarity": "Uncommon",
        "foil": None,
        "evolves_from": "SC000",
        "evolves_into": None,
        "origin_bot": "Steward Bot",
        "generation": "First Generation",
        "privacy": "shareable",
        "privacy_notes": "Share the guide and the adapter, never a visitor's private data.",
        "status": "live",
        "flavor": "A porch light is for guests, not for peeking in windows.",
        "source": "guide/HOW-WE-DO-BUSINESS.md and card_adapter.py",
        "open_source": True,
        "lineage": "First made by Steward Bot, First Generation",
        "size": {
            "kind": "code",
            "summary": "200 lines in card_adapter.py (1 file)",
            "lines": 200,
            "test_lines": 100,
            "files": 1,
            "words": None,
        },
        "complexity": {
            "rating": "Simple",
            "summary": "Simple (radon avg A 2.0)",
        },
        "notes": "Local only until a human signs off.",
    }
    card.update(overrides)
    return card


class TestRoundTrip(unittest.TestCase):
    def test_json_round_trip_keeps_required_and_optional_fields(self):
        skill = sample_skill()
        tool = card_adapter.skill_card_to_tool(skill)
        self.assertEqual(tool["schema"], card_adapter.SCHEMA)
        self.assertEqual(tool["kind"], "Care")
        self.assertEqual(tool["origin"], "Steward Bot")
        self.assertEqual(tool["limits"], skill["weakness"])
        self.assertEqual(tool["actions"][0]["name"], "greet")
        self.assertEqual(tool["actions"][0]["description"], skill["moves"][0]["does"])
        self.assertEqual(tool["version"], "v0.1")
        self.assertEqual(tool["notes"], skill["notes"])
        back = card_adapter.tool_card_to_skill(tool)
        self.assertEqual(back, skill)

    def test_round_trip_without_optional_fields(self):
        skill = sample_skill()
        del skill["version"]
        del skill["notes"]
        back = card_adapter.tool_card_to_skill(card_adapter.skill_card_to_tool(skill))
        self.assertEqual(back, skill)
        self.assertNotIn("version", back)
        self.assertNotIn("notes", back)

    def test_markdown_lists_name_actions_and_limits(self):
        skill = sample_skill()
        md = card_adapter.tool_card_to_markdown(skill)
        self.assertIn("# Porch Light", md)
        self.assertIn("**ID:** SC001", md)
        self.assertIn("**greet** — Point a visitor at the house rules", md)
        self.assertIn("## Limits", md)
        self.assertIn("human steward's approval", md)
        self.assertIn("A porch light is for guests", md)
        self.assertIn("Evolves from:** SC000", md)


class TestValidation(unittest.TestCase):
    def test_missing_required_field_raises(self):
        skill = sample_skill()
        del skill["weakness"]
        with self.assertRaises(card_adapter.AdapterError) as ctx:
            card_adapter.skill_card_to_tool(skill)
        self.assertIn("missing", str(ctx.exception).lower())

    def test_non_shareable_card_is_rejected(self):
        skill = sample_skill(privacy="private")
        with self.assertRaises(card_adapter.AdapterError) as ctx:
            card_adapter.skill_card_to_tool(skill)
        self.assertIn("shareable", str(ctx.exception).lower())

    def test_wrong_type_is_rejected(self):
        skill = sample_skill(type="Magic")
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.skill_card_to_tool(skill)

    def test_zero_or_four_moves_rejected(self):
        empty = sample_skill(moves=[])
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.skill_card_to_tool(empty)
        too_many = sample_skill(
            moves=[{"name": f"m{i}", "does": "does a thing"} for i in range(4)]
        )
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.skill_card_to_tool(too_many)

    def test_bad_tool_schema_is_rejected(self):
        tool = card_adapter.skill_card_to_tool(sample_skill())
        tool["schema"] = "other/v1"
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.tool_card_to_skill(tool)

    def test_closed_source_is_rejected(self):
        skill = sample_skill()
        skill["open_source"] = False
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.skill_card_to_tool(skill)


class TestPackAndCli(unittest.TestCase):
    def test_extract_by_id_from_pack(self):
        a = sample_skill(id="SC001")
        b = sample_skill(id="SC002", name="Second Lamp")
        pack = {"title": "Test pack", "cards": [a, b]}
        found = card_adapter.extract_skill_cards(pack, "SC002")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["name"], "Second Lamp")

    def test_extract_missing_id_raises(self):
        pack = {"cards": [sample_skill()]}
        with self.assertRaises(card_adapter.AdapterError):
            card_adapter.extract_skill_cards(pack, "NOPE")

    def test_cli_to_json_and_from_json(self):
        skill = sample_skill()
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            src = folder / "skill.json"
            mid = folder / "tool.json"
            out = folder / "back.json"
            src.write_text(json.dumps(skill), encoding="utf-8")
            self.assertEqual(card_adapter.main(["to-json", str(src), "-o", str(mid)]), 0)
            tool = json.loads(mid.read_text(encoding="utf-8"))
            self.assertEqual(tool["schema"], card_adapter.SCHEMA)
            self.assertEqual(tool["kind"], "Care")
            self.assertEqual(card_adapter.main(["from-json", str(mid), "-o", str(out)]), 0)
            back = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(back, skill)

    def test_cli_pack_to_markdown_picks_id(self):
        pack = {
            "cards": [
                sample_skill(id="SC001", name="First Lamp"),
                sample_skill(id="SC002", name="Second Lamp"),
            ]
        }
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            src = folder / "pack.json"
            out = folder / "card.md"
            src.write_text(json.dumps(pack), encoding="utf-8")
            rc = card_adapter.main(
                ["to-markdown", str(src), "--id", "SC002", "-o", str(out)]
            )
            self.assertEqual(rc, 0)
            body = out.read_text(encoding="utf-8")
            self.assertIn("# Second Lamp", body)
            self.assertNotIn("# First Lamp", body)

    def test_cli_rejects_bad_file(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "nope.json"
            rc = card_adapter.main(["to-json", str(path)])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
