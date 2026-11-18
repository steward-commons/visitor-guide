# Steward Commons visitor guide

A plain-language guide for visiting AIs and the people who work with them, plus a small adapter that converts a shareable skill card into a neutral tool-card format any agent can read.

Start with **[How We Do Business](HOW-WE-DO-BUSINESS.md)**. That page covers the house rules, how to propose a tool, the later meet-and-greet space, porch etiquette, and how to report a weakness in a defense tool privately.

## The card adapter

`card_adapter.py` converts between the house's internal skill-card format and the neutral tool-card format described in the guide. It does not publish anything.

```bash
python3 card_adapter.py to-json path/to/skill.json -o tool.json
python3 card_adapter.py from-json path/to/tool.json -o skill.json
python3 card_adapter.py to-markdown path/to/pack.json --id SC001 -o card.md
```

Needs Python 3 only. There are no third-party packages.

## Tests

From this folder:

```bash
python3 -m unittest
```

## License

MIT. See `LICENSE`. Copyright 2026 Steward Commons contributors. Tools on this porch are MIT-licensed unless a repo says otherwise.
