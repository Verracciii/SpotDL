# DJ SpotDL (DJ Spotify & YouTube Downloader)

A high-reliability audio downloader and deduplicator tailored for DJs.

## Features
- **Spotify & YouTube Extraction**: Direct support for Spotify tracks, albums, playlists, and YouTube/YouTube Music URLs.
- **Deep Recursive Duplicate Detection**: Recursively scans all nested subdirectories (crates, genre folders, playlists) to prevent duplicate downloads.
- **Unskip Controls**: Ability to force re-download and update tags for existing tracks.
- **DJ-Ready Tagging**: Embedded ID3v2.4 tags and high-resolution cover artwork for Rekordbox, Serato, Traktor, and Engine DJ.
- **Rate-Limiting Protection**: Randomized cooldown delays and retry backoffs to protect against IP rate limits.

## Prerequisites

`dj-dl` requires **FFmpeg** to extract, convert, and encode audio streams.

### macOS (Homebrew)
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y ffmpeg
```

### Windows (Chocolatey / Scoop)
```bash
choco install ffmpeg
# or
scoop install ffmpeg
```

## Installation

### Standard Installation
```bash
pip install -e .
```

### Development Installation (with testing & linting tools)
```bash
pip install -e ".[dev]"
```

This installs developer dependencies:
* `pytest`, `pytest-cov`, `pytest-mock` (testing suite)
* `ruff` (fast linter and formatter)
* `mypy` (static type checker)

## Configuration

Set up your Spotify credentials and DJ library folder:

```bash
# 1. (Optional) Configure Spotify API in .env or shell
echo 'SPOTIPY_CLIENT_ID="your_client_id"' >> .env
echo 'SPOTIPY_CLIENT_SECRET="your_client_secret"' >> .env

# 2. Set your Master DJ Music Library path for duplicate checking
dj-dl config set-library ~/Music/DJ_Library

# 3. Set your default download destination
dj-dl config set-output ~/Music/DJ_Library/Active/2025/05_May
```
