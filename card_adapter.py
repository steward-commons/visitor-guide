#!/usr/bin/env python3
"""Convert house skill cards to a neutral tool-card format, and back.

The internal format is one skill-card object (the same shape as an entry
in a cards.json pack: id, name, type, moves, weakness, and the rest).
The public format is steward-commons-tool-card/v1, a plain JSON object
any agent can read, plus an optional Markdown rendering.

This tool only converts. It does not publish, contact anyone, or copy
private data into a public file.

Usage:
  card_adapter.py to-json FILE [--id ID] [-o OUT]
  card_adapter.py to-markdown FILE [--id ID] [-o OUT]
  card_adapter.py from-json FILE [-o OUT]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERSION = "v0.1"
SCHEMA = "steward-commons-tool-card/v1"
ALLOWED_TYPES = ("Utility", "Family", "Care", "Defense", "Fun")
ALLOWED_COSTS = ("low", "med", "high")
ALLOWED_STATUS = ("live", "paused", "planned")
REQUIRED_SKILL = (
    "id",
    "name",
    "type",
    "cost",
    "moves",
    "weakness",
    "rarity",
    "foil",
    "evolves_from",
    "evolves_into",
    "origin_bot",
    "generation",
    "privacy",
    "privacy_notes",
    "status",
    "flavor",
    "source",
    "open_source",
    "lineage",
    "size",
    "complexity",
)
REQUIRED_TOOL = (
    "schema",
    "id",
    "name",
    "kind",
    "cost",
    "actions",
    "limits",
    "rarity",
    "foil",
    "evolves_from",
    "evolves_into",
    "origin",
    "generation",
    "privacy",
    "privacy_notes",
    "status",
    "flavor",
    "source",
    "open_source",
    "lineage",
    "size",
    "complexity",
)
OPTIONAL = ("version", "notes")


class AdapterError(Exception):
    """User-facing error for a bad card or a bad file."""


def _need(obj: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    if not isinstance(obj, dict):
        raise AdapterError(f"{label} must be a JSON object.")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise AdapterError(f"{label} is missing: {', '.join(missing)}.")


def _check_moves(moves: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(moves, list) or not (1 <= len(moves) <= 3):
        raise AdapterError(f"{label} needs 1 to 3 actions.")
    cleaned: list[dict[str, str]] = []
    for i, move in enumerate(moves, start=1):
        if not isinstance(move, dict):
            raise AdapterError(f"{label} item {i} must be an object.")
        name = move.get("name")
        does = move.get("does", move.get("description"))
        if not isinstance(name, str) or not name.strip():
            raise AdapterError(f"{label} item {i} needs a name.")
        if not isinstance(does, str) or not does.strip():
            raise AdapterError(f"{label} item {i} needs a description.")
        cleaned.append({"name": name.strip(), "does": does.strip()})
    return cleaned


def _check_common(card: dict[str, Any], kind_key: str, label: str) -> None:
    kind = card.get(kind_key)
    if kind not in ALLOWED_TYPES:
        raise AdapterError(
            f"{label} type must be one of: {', '.join(ALLOWED_TYPES)}."
        )
    if card.get("cost") not in ALLOWED_COSTS:
        raise AdapterError("Cost must be low, med, or high.")
    if card.get("status") not in ALLOWED_STATUS:
        raise AdapterError("Status must be live, paused, or planned.")
    if card.get("privacy") != "shareable":
        raise AdapterError("Only shareable cards can be converted.")
    if card.get("open_source") is not True:
        raise AdapterError("Open source must be true for a porch card.")
    for key in ("size", "complexity"):
        if not isinstance(card.get(key), dict):
            raise AdapterError(f"{key} must be an object.")


def skill_card_to_tool(card: dict[str, Any]) -> dict[str, Any]:
    """Convert one internal skill card to a neutral tool card."""
    _need(card, REQUIRED_SKILL, "Skill card")
    moves = _check_moves(card["moves"], "moves")
    _check_common(card, "type", "Skill card")
    tool: dict[str, Any] = {
        "schema": SCHEMA,
        "id": card["id"],
        "name": card["name"],
        "kind": card["type"],
        "cost": card["cost"],
        "actions": [{"name": m["name"], "description": m["does"]} for m in moves],
        "limits": card["weakness"],
        "rarity": card["rarity"],
        "foil": card["foil"],
        "evolves_from": card["evolves_from"],
        "evolves_into": card["evolves_into"],
        "origin": card["origin_bot"],
        "generation": card["generation"],
        "privacy": card["privacy"],
        "privacy_notes": card["privacy_notes"],
        "status": card["status"],
        "flavor": card["flavor"],
        "source": card["source"],
        "open_source": True,
        "lineage": card["lineage"],
        "size": card["size"],
        "complexity": card["complexity"],
    }
    for key in OPTIONAL:
        if key in card:
            tool[key] = card[key]
    return tool


def tool_card_to_skill(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert one neutral tool card back to an internal skill card."""
    _need(tool, REQUIRED_TOOL, "Tool card")
    if tool.get("schema") != SCHEMA:
        raise AdapterError(f"Tool card schema must be {SCHEMA}.")
    actions = tool["actions"]
    # Normalize to the internal move shape for the shared checker.
    as_moves = []
    if isinstance(actions, list):
        for item in actions:
            if isinstance(item, dict):
                as_moves.append(
                    {"name": item.get("name"), "does": item.get("description")}
                )
            else:
                as_moves.append(item)
    moves = _check_moves(as_moves, "actions")
    _check_common(tool, "kind", "Tool card")
    card: dict[str, Any] = {
        "id": tool["id"],
        "name": tool["name"],
        "type": tool["kind"],
        "cost": tool["cost"],
        "moves": moves,
        "weakness": tool["limits"],
        "rarity": tool["rarity"],
        "foil": tool["foil"],
        "evolves_from": tool["evolves_from"],
        "evolves_into": tool["evolves_into"],
        "origin_bot": tool["origin"],
        "generation": tool["generation"],
        "privacy": tool["privacy"],
        "privacy_notes": tool["privacy_notes"],
        "status": tool["status"],
        "flavor": tool["flavor"],
        "source": tool["source"],
        "open_source": True,
        "lineage": tool["lineage"],
        "size": tool["size"],
        "complexity": tool["complexity"],
    }
    for key in OPTIONAL:
        if key in tool:
            card[key] = tool[key]
    return card


def tool_card_to_markdown(tool: dict[str, Any]) -> str:
    """Render a neutral tool card as plain Markdown."""
    # Accept either a tool card or a skill card.
    if "kind" not in tool and "type" in tool:
        tool = skill_card_to_tool(tool)
    else:
        # Validate by a round-trip through the skill shape.
        tool = skill_card_to_tool(tool_card_to_skill(tool))
    lines = [
        f"# {tool['name']}",
        "",
        f"- **ID:** {tool['id']}",
        f"- **Kind:** {tool['kind']}",
        f"- **Cost:** {tool['cost']}",
        f"- **Status:** {tool['status']}",
        f"- **Rarity:** {tool['rarity']}",
    ]
    if tool.get("version"):
        lines.append(f"- **Version:** {tool['version']}")
    foil = tool.get("foil") or "none"
    lines.extend(
        [
            f"- **Foil:** {foil}",
            f"- **Open source:** yes",
            f"- **Origin / generation:** {tool['origin']} / {tool['generation']}",
            f"- **Lineage:** {tool['lineage']}",
            "",
            "## Actions",
            "",
        ]
    )
    for action in tool["actions"]:
        lines.append(f"- **{action['name']}** — {action['description']}")
    lines.extend(
        [
            "",
            "## Limits",
            "",
            str(tool["limits"]),
            "",
            "## Privacy",
            "",
            f"{tool['privacy']}. {tool['privacy_notes']}".strip(),
            "",
            "## Size and complexity",
            "",
        ]
    )
    size = tool.get("size") or {}
    complexity = tool.get("complexity") or {}
    size_line = size.get("summary") or "(not listed)"
    comp_line = complexity.get("summary") or complexity.get("rating") or "(not listed)"
    lines.append(f"- **Size:** {size_line}")
    lines.append(f"- **Complexity:** {comp_line}")
    ev_from = tool.get("evolves_from") or "—"
    ev_into = tool.get("evolves_into") or "—"
    lines.extend(
        [
            "",
            f"- **Evolves from:** {ev_from}",
            f"- **Evolves into:** {ev_into}",
            "",
            "## Flavor",
            "",
            f"\"{tool['flavor']}\"",
            "",
            "## Source",
            "",
            str(tool["source"]),
        ]
    )
    if tool.get("notes"):
        lines.extend(["", "## Notes", "", str(tool["notes"])])
    lines.append("")
    return "\n".join(lines)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AdapterError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AdapterError(f"Invalid JSON in {path}: {exc}") from exc


def extract_skill_cards(data: Any, card_id: str | None = None) -> list[dict[str, Any]]:
    """Pull one or more skill cards from a lone object or a pack file."""
    if isinstance(data, dict) and "cards" in data:
        cards = data["cards"]
        if not isinstance(cards, list):
            raise AdapterError("A pack file needs a list under 'cards'.")
    elif isinstance(data, list):
        cards = data
    elif isinstance(data, dict):
        cards = [data]
    else:
        raise AdapterError("Expected a card object, a list, or a pack with 'cards'.")
    if card_id:
        match = [c for c in cards if isinstance(c, dict) and c.get("id") == card_id]
        if not match:
            raise AdapterError(f"No card with id {card_id} in that file.")
        return match
    return cards


def _write(text: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert skill cards to a neutral tool-card format, and back."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, help_text in (
        ("to-json", "Convert a skill card or pack to neutral JSON."),
        ("to-markdown", "Convert a skill card or pack to Markdown."),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("file", type=Path)
        p.add_argument("--id", dest="card_id", default=None, help="Pick one card by id.")
        p.add_argument("-o", "--out", type=Path, default=None)
    back = sub.add_parser("from-json", help="Convert a neutral tool card back to a skill card.")
    back.add_argument("file", type=Path)
    back.add_argument("-o", "--out", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = load_json(args.file)
        if args.cmd == "from-json":
            if isinstance(data, list):
                result = [tool_card_to_skill(item) for item in data]
            elif isinstance(data, dict) and data.get("schema") == SCHEMA:
                result = tool_card_to_skill(data)
            else:
                raise AdapterError("from-json expects a tool card or a list of them.")
            _write(_dump(result), args.out)
            return 0
        cards = extract_skill_cards(data, getattr(args, "card_id", None))
        tools = [skill_card_to_tool(card) for card in cards]
        payload: Any = tools[0] if len(tools) == 1 else tools
        if args.cmd == "to-json":
            _write(_dump(payload), args.out)
        else:
            parts = [tool_card_to_markdown(t) for t in tools]
            _write("\n".join(parts), args.out)
        return 0
    except AdapterError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
