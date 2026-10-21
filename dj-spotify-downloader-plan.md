# DJ Spotify & YouTube Downloader Plan

## Top-Level Overview
A modular, high-reliability Python CLI tool (with an optional future Web UI layer) designed for DJs to download Spotify tracks/playlists and direct YouTube/YouTube Music links. It fetches high-quality audio with `yt-dlp`, applies full ID3 metadata and high-res artwork, performs deep recursive scans across nested subdirectories to detect and prevent duplicate downloads (with full unskip / force-download capability), and enforces rate-limiting safeguards.

---

## Architecture Design

```
URL Input (Spotify Track/Playlist/Album OR YouTube Video/Playlist)
                           │
                           ▼
              ┌──────────────────────────┐
              │    Link & Source Router  │
              └────────────┬─────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│  Spotify Metadata      │  │  YouTube Direct Info   │
│  Extractor             │  │  Extractor             │
└────────────┬───────────┘  └────────────┬───────────┘
             └─────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ Deep Recursive Subdir    │
              │ Duplicate Indexer        │
              └────────────┬─────────────┘
                           │
          [Duplicate & not --force?]
          ├── YES ➔ Log / Record Skipped (can unskip via flag)
          └── NO  ➔ Proceed to Download
                           │
                           ▼
              ┌──────────────────────────┐
              │  yt-dlp Audio Downloader │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  ID3 Metadata & Artwork  │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  Rate Limiter & Jitter   │
              └──────────────────────────┘
```

---

## Sub-Tasks

### Sub-Task 1: Project Scaffolding & Configuration
- **Intent**: Establish project structure, dependencies, and environment configuration.
- **Expected Outcomes**: Clean package structure with config loading for Spotify credentials, default audio formats (MP3 320kbps / FLAC), download folders, and rate-limit settings.
- **Todo List**:
  1. Create project folder structure (`src/dj_downloader/`, `tests/`).
  2. Setup `pyproject.toml` or `requirements.txt` (`yt-dlp`, `spotipy`, `mutagen`, `rich`, `typer`, `pydantic`).
  3. Implement configuration management (`config.py`) loading settings and `.env` variables safely.
- **Relevant Context**: `src/dj_downloader/config.py`
- **Status**: `[ ] pending`

---

### Sub-Task 2: URL Router & Metadata Extractors (Spotify & YouTube)
- **Intent**: Parse and extract structured metadata from Spotify URLs (Track, Album, Playlist) AND Direct YouTube / YouTube Music URLs (Videos, Playlists).
- **Expected Outcomes**: Unified list of `TrackInfo` objects regardless of source (Spotify or direct YouTube).
- **Todo List**:
  1. Define unified `TrackInfo` data model (title, artist, album, duration_ms, isrc, release_date, cover_url, source_url).
  2. Implement URL router detecting Spotify vs YouTube vs YouTube Music.
  3. Implement Spotify metadata extraction (via Web API / spotipy).
  4. Implement YouTube metadata extraction directly from `yt-dlp` info-dict (parsing Artist - Title from title/uploader).
- **Relevant Context**: `src/dj_downloader/spotify.py`, `src/dj_downloader/youtube.py`, `src/dj_downloader/router.py`, `src/dj_downloader/models.py`
- **Status**: `[ ] pending`

---

### Sub-Task 3: Deep Recursive Directory Duplicate Detection & Unskip Engine
- **Intent**: Recursively walk all nested subdirectories (crates, genres, playlist folders) in the DJ's music collection, index existing audio files, detect duplicates, and provide options to skip or force unskip/redownload.
- **Expected Outcomes**: Fast in-memory lookup index that checks: (1) normalized artist + title, (2) ISRC / Spotify ID tags, and (3) sanitized filenames across all nested subdirectories. Supports `--force` or interactive unskipping.
- **Todo List**:
  1. Create `LibraryIndexer` with `os.walk` / `pathlib.Path.rglob` to deeply scan all nested subdirectories for `.mp3`, `.flac`, `.m4a`, `.aiff`, `.wav`.
  2. Read embedded ID3/Vorbis tags via `mutagen` for accurate matching across all discovered files.
  3. Implement fuzzy/normalized comparison (strip punctuation, lowercase, normalize feat./ft.).
  4. Store file location metadata so the CLI can report exact duplicate location (e.g., "Found existing in `House/TechHouse/track.mp3`").
  5. Add unskip logic: allow overriding duplicates via `--force` / `--overwrite` or selective unskipping.
- **Relevant Context**: `src/dj_downloader/dedup.py`
- **Status**: `[ ] pending`

---

### Sub-Task 4: Audio Downloader & Matcher with yt-dlp
- **Intent**: Download the best audio stream for Spotify matches or direct YouTube URLs.
- **Expected Outcomes**: High-quality audio downloaded with duration verification to prevent downloading snippets or live versions.
- **Todo List**:
  1. Construct optimized search queries for Spotify tracks (or direct extraction for YouTube links).
  2. Configure `yt-dlp` options for best audio extraction (preferred bitrate, audio-only extraction via ffmpeg).
  3. Implement duration sanity check for Spotify matches (reject streams differing by >15s).
  4. Handle download errors, age restrictions, and temporary connection failures gracefully.
- **Relevant Context**: `src/dj_downloader/downloader.py`
- **Status**: `[ ] pending`

---

### Sub-Task 5: Tagging, Artwork Injection & File Organization
- **Intent**: Embed pristine metadata, high-resolution album artwork, and DJ-friendly tags into the downloaded audio file.
- **Expected Outcomes**: Fully tagged MP3/FLAC files ready for Serato, Rekordbox, Traktor, or Engine DJ.
- **Todo List**:
  1. Download and process album artwork.
  2. Write standard ID3v2.4 / Vorbis tags using `mutagen` (Title, Artist, Album, Year, Track Number, Genre, ISRC).
  3. Embed cover art into audio container.
  4. Format destination filename according to customizable template (e.g. `{Artist} - {Title}.mp3`).
- **Relevant Context**: `src/dj_downloader/tagger.py`
- **Status**: `[ ] pending`

---

### Sub-Task 6: Rate Limiting & Cooldown Protection
- **Intent**: Protect user IP from rate limiting or blocking during batch downloads.
- **Expected Outcomes**: Configurable delay with randomized jitter between consecutive downloads, auto-retry with exponential backoff on HTTP 429 errors.
- **Todo List**:
  1. Implement `RateLimiter` class with configurable `min_delay` and `max_delay` (e.g. 2s to 6s random jitter).
  2. Implement exponential backoff for transient network / rate-limit errors.
  3. Add optional cookie support for `yt-dlp` if bot checks are encountered.
- **Relevant Context**: `src/dj_downloader/limiter.py`
- **Status**: `[ ] pending`

---

### Sub-Task 7: CLI Interface with Unskip Controls & Rich Progress
- **Intent**: Provide a fast, beautiful, and intuitive command-line interface.
- **Expected Outcomes**: Interactive CLI using `typer` and `rich` featuring progress bars, summary tables, and unskip/force flags.
- **Todo List**:
  1. Build CLI commands:
     - `dj-dl download <url> [--output-dir] [--format] [--force] [--unskip-all]`
     - `dj-dl scan <directory>` (inspect existing library and all nested subdirectories)
  2. Display real-time progress bar with `rich.progress`.
  3. Print final summary report: newly downloaded, skipped duplicates (with nested file paths), force-unskipped, and failed items.
- **Relevant Context**: `src/dj_downloader/cli.py`
- **Status**: `[ ] pending`

---

### Sub-Task 8: Testing & Verification
- **Intent**: Validate each module with unit tests and mock integration tests.
- **Expected Outcomes**: Test suite verifying nested directory deduplication logic, unskip overrides, URL routing, YouTube/Spotify metadata parsing, and rate limiting.
- **Todo List**:
  1. Write unit tests for nested subdirectory scanning and duplicate detection.
  2. Write unit tests for Spotify & YouTube URL routing.
  3. Write unit tests for ID3 tagging.
- **Relevant Context**: `tests/test_dedup.py`, `tests/test_router.py`, `tests/test_tagger.py`
- **Status**: `[ ] pending`
