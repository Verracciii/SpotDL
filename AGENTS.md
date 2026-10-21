# Development Guide & Repository Rules

This document outlines the architecture, engineering principles, development workflow, and coding standards for all human developers and AI agents working on **DJ Spotify & YouTube Downloader (`dj-spotdl`)**.

---

## 1. Core Mission & Scope
The application is a high-reliability audio extraction and metadata tagging CLI tool designed for DJs. It pulls tracks and playlists from Spotify and direct YouTube/YouTube Music URLs, tags them with complete ID3v2.4 metadata and high-resolution cover art, deeply scans music directories (including all nested subdirectories) to detect and skip duplicates, and provides unskip/force-download controls.

---

## 2. Engineering Principles

1. **Test-Driven Development (TDD)**:
   - Always write tests before or alongside implementation.
   - Run `pytest` before finalizing any subtask.
   - Mock all external network calls (Spotify API, YouTube network queries) in automated unit tests.
2. **Minimal & Surgical Changes**:
   - Produce the minimal change that solves the issue.
   - Do not introduce unnecessary abstractions or bloat.
3. **Security Standards**:
   - Never hardcode API keys, secrets, or personal paths.
   - Load configuration via `pydantic-settings` from environment variables (`.env`).
   - Strictly bind local servers (if added) to `127.0.0.1`.
4. **Code Quality**:
   - Formatter & Linter: **Ruff** (line length: 100).
   - Type Hints: Full static typing with strict type annotations checked via **mypy**.

---

## 3. Architecture & Project Layout

```
SpotDL/
├── pyproject.toml              # Build backend (hatchling), dependencies, ruff & pytest config
├── .gitignore                  # Git exclusions (audio files, venvs, cache, macOS, .bob)
├── .editorconfig               # Consistent cross-editor whitespace & indentation
├── AGENTS.md                   # This development guide
├── dj-spotify-downloader-plan.md # Architectural plan and subtasks
├── src/
│   └── dj_downloader/
│       ├── __init__.py
│       ├── models.py           # Pydantic models (TrackInfo, DuplicateMatch, DownloadResult)
│       ├── config.py           # Application settings loaded from env
│       ├── router.py           # Unified URL router (Spotify vs YouTube)
│       ├── spotify.py          # Spotify metadata extractor (API & embed fallback)
│       ├── youtube.py          # YouTube & YouTube Music extractor
│       ├── dedup.py            # Deep recursive directory scanner & duplicate indexer
│       ├── downloader.py       # yt-dlp audio downloader & duration validator
│       ├── tagger.py           # Mutagen ID3v2.4 / Vorbis tagger & artwork embedder
│       ├── limiter.py          # Rate limiting, jitter cooldown, and exponential backoff
│       └── cli.py              # Typer + Rich interactive CLI
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures and mock responses
    ├── test_models.py
    ├── test_router.py
    ├── test_spotify.py
    ├── test_youtube.py
    ├── test_dedup.py
    ├── test_downloader.py
    └── test_tagger.py
```

---

## 4. Development Workflow

### Running Tests
```bash
pytest
# Or with coverage
pytest --cov=dj_downloader
```

### Running Linting & Formatting
```bash
ruff check .
ruff format .
```

### Running Static Type Checks
```bash
mypy src
```

---

## 5. Sub-Task Execution Rules for Agents

- **Step-by-Step Focus**: Complete exactly one sub-task at a time.
- **Verification Gate**: Never mark a subtask as complete until corresponding tests have been written and run with passing status.
- **Preserve Cleanliness**: Do not commit downloaded media files (`*.mp3`, `*.flac`, etc.) or `.env` files.
