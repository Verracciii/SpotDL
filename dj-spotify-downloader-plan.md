# DJ Spotify & YouTube Downloader Plan

## Top-Level Overview
A modular, high-reliability Python CLI tool designed for DJs to download Spotify tracks/playlists and direct YouTube/YouTube Music links. It features:
- **First-Run Setup & Config Management**: Prompts on first run for the highest-level master DJ Library directory and allows permanently updating library/output paths via CLI.
- **Smart Output Organization**: Automatically creates organized subfolders per playlist/album or uses custom output directories.
- **Deep Recursive Deduplication**: Recursively indexes all nested subdirectories in the master DJ library to detect and prevent duplicates, with unskip/force-download controls.
- **Audio Matching & Tagging**: High-quality audio via `yt-dlp` with complete ID3v2.4 tags and high-res cover art.
- **Rate-Limiting Protection**: Randomized cooldown delays and backoff to protect against IP blocks.

---

## Sub-Tasks

### Sub-Task 1: Configuration & First-Time Setup Manager
- **Intent**: Manage persistent user configuration (`~/.config/dj-spotdl/config.json`), first-run prompt for root DJ library directory, and CLI config commands.
- **Status**: `[x] done (updated)`

---

### Sub-Task 2: Unified URL Router & Metadata Extractors (Spotify & YouTube)
- **Intent**: Extract structured metadata for tracks, albums, and playlists from Spotify and YouTube.
- **Status**: `[x] done`

---

### Sub-Task 3: Deep Recursive Directory Duplicate Detection & Indexer
- **Intent**: Recursively walk all nested subdirectories (crates, genres, playlist folders) under the master DJ library, index existing audio files, detect duplicates, and provide options to skip or force unskip/redownload.
- **Expected Outcomes**: Fast in-memory lookup index that checks: (1) normalized artist + title, (2) ISRC / Spotify ID tags, and (3) sanitized filenames across all nested subdirectories. Supports `--force` or interactive unskipping.
- **Todo List**:
  1. Create `LibraryIndexer` with recursive scanning (`rglob`) across all subdirectories of the configured master DJ library.
  2. Read embedded ID3/Vorbis tags via `mutagen` for accurate matching across all discovered files.
  3. Implement fuzzy/normalized comparison (strip punctuation, lowercase, normalize feat./ft.).
  4. Store file location metadata so the CLI reports exact duplicate location (e.g., "Found existing in `House/TechHouse/track.mp3`").
  5. Add unskip logic: allow overriding duplicates via `--force` / `--overwrite` or selective unskipping.
- **Relevant Context**: `src/dj_downloader/dedup.py`, `tests/test_dedup.py`
- **Status**: `[ ] pending`

---

### Sub-Task 4: Audio Downloader & Matcher with yt-dlp
- **Intent**: Download the best audio stream for Spotify matches or direct YouTube URLs.
- **Relevant Context**: `src/dj_downloader/downloader.py`
- **Status**: `[ ] pending`

---

### Sub-Task 5: Tagging, Artwork Injection & Playlist Subfolder Organization
- **Intent**: Embed pristine metadata, high-resolution album artwork, and DJ-friendly tags into the downloaded audio file, and organize playlist downloads into dedicated subfolders.
- **Relevant Context**: `src/dj_downloader/tagger.py`
- **Status**: `[ ] pending`

---

### Sub-Task 6: Rate Limiting & Cooldown Protection
- **Intent**: Protect user IP from rate limiting or blocking during batch downloads.
- **Relevant Context**: `src/dj_downloader/limiter.py`
- **Status**: `[ ] pending`

---

### Sub-Task 7: Rich Interactive CLI with Config & Unskip Controls
- **Intent**: Interactive CLI (`typer` + `rich`) featuring first-run setup wizard, `config` command (`dj-dl config set-library ...`), playlist progress bars, and unskip flags.
- **Relevant Context**: `src/dj_downloader/cli.py`
- **Status**: `[ ] pending`

---

### Sub-Task 8: Testing & Verification
- **Intent**: Full test suite validating config manager, deduplication logic, unskip overrides, URL routing, YouTube/Spotify metadata parsing, and rate limiting.
- **Relevant Context**: `tests/`
- **Status**: `[ ] pending`
