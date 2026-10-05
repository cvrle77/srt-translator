# SRT Translator

A desktop app (PyQt6) for translating `.srt` subtitle files between any languages and any subject matter. The language pair, domain, and style are **not hardcoded** — they come entirely from editable prompts. It enforces hard line-length and characters-per-second (CPS) limits, and uses the OpenRouter API for translation.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Any → Any** language and topic, via **OpenRouter** — direction, domain, and style are all set by the prompts (works with any OpenRouter model).
- **Fully prompt-driven** — ships with one example prompt; replace it to suit any language pair, genre, or style.
- Strict **line-length** rules (max ~89 chars, 45+45 splits) and **CPS** enforcement with automatic shortening.
- **Manual retranslation** of individual blocks (right-click a row).
- **Line-splitting mode** for turning long lines into two balanced lines.
- Editable **prompts** and **model list** from the Settings dialog.
- Custom subtitle table with synchronized scrolling and per-block highlighting.
- API key stored in a **separate `secrets.json`** that is created automatically and never committed.

## Requirements

- Python 3.9+
- Windows (primary target; the UI is PyQt6 so it may run on macOS/Linux too)
- An [OpenRouter](https://openrouter.ai/) API key

## Run from source

```bash
pip install -r requirements.txt
python app.py
```

On first run the app creates `secrets.json` next to the script (or next to the executable when frozen) and shows a dialog with its exact path if no key is set. Paste your OpenRouter key there, or enter it in **Settings → API Keys**.

## Build a standalone executable (Windows)

```bash
pip install pyinstaller
pyinstaller SRT-Translator.spec
```

The build lands in `dist/`. Binaries are intentionally not committed — attach them to a GitHub **Release**.

## Configuration

| File | Purpose | Committed? |
|---|---|---|
| `config.json` | Prompts, OpenRouter model list, window geometry | yes (contains **no** secrets) |
| `secrets.json` | OpenRouter API key only | **no** — created automatically, gitignored |

API keys are never written to `config.json`. If a key is found there from an older version, the app migrates it into `secrets.json` on load.

## Project layout

```
.
├── app.py                 # main application (PyQt6)
├── SRT-Translator.spec    # PyInstaller build spec
├── config.json            # default settings / prompts
├── requirements.txt
├── .github/workflows/ci.yml
└── README.md
```

## Versioning

The version is **derived automatically from git tags** — there is no hardcoded
number to bump by hand. `build.py` reads the nearest `vX.Y.Z` tag and bakes the
result, together with the short git hash and build date, into `_version.py`; the
app shows them in the window title and status bar.

- On a tag: `1.2.0`
- Commits after the last tag: next patch as a dev build, e.g. `1.2.1.dev7`
- Uncommitted changes: `.dirty` suffix

To cut a release:

```bash
git tag v1.2.0
git push origin v1.2.0
python build.py
```

## License

[MIT](LICENSE)
