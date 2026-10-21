# DJ SpotDL (DJ Spotify & YouTube Downloader)

A high-reliability audio downloader and deduplicator tailored for DJs.

## Features
- **Spotify & YouTube Extraction**: Direct support for Spotify tracks, albums, playlists, and YouTube/YouTube Music URLs.
- **Deep Recursive Duplicate Detection**: Recursively scans all nested subdirectories (crates, genre folders, playlists) to prevent duplicate downloads.
- **Unskip Controls**: Ability to force re-download and update tags for existing tracks.
- **DJ-Ready Tagging**: Embedded ID3v2.4 tags and high-resolution cover artwork for Rekordbox, Serato, Traktor, and Engine DJ.
- **Rate-Limiting Protection**: Randomized cooldown delays and retry backoffs to protect against IP rate limits.

## Installation
```bash
pip install -e .
```
