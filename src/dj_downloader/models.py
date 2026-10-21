"""Data models for DJ Spotify & YouTube Downloader."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AudioFormat(str, Enum):
    """Supported output audio formats."""

    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    WAV = "wav"


class SourceType(str, Enum):
    """Origin source of the track."""

    SPOTIFY_TRACK = "spotify_track"
    SPOTIFY_ALBUM = "spotify_album"
    SPOTIFY_PLAYLIST = "spotify_playlist"
    YOUTUBE_VIDEO = "youtube_video"
    YOUTUBE_PLAYLIST = "youtube_playlist"


class TrackInfo(BaseModel):
    """Metadata representing a single audio track."""

    title: str
    artists: list[str] = Field(default_factory=list)
    album: str | None = None
    album_artist: str | None = None
    release_date: str | None = None
    duration_ms: int = 0
    isrc: str | None = None
    spotify_id: str | None = None
    source_url: str
    source_type: SourceType = SourceType.SPOTIFY_TRACK
    cover_url: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    genre: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def primary_artist(self) -> str:
        """Return primary artist or 'Unknown Artist'."""
        return self.artists[0] if self.artists else "Unknown Artist"

    @property
    def artist_string(self) -> str:
        """Return comma-separated artists."""
        return ", ".join(self.artists) if self.artists else "Unknown Artist"

    @property
    def display_name(self) -> str:
        """Return formatted artist - title string."""
        return f"{self.primary_artist} - {self.title}"

    @property
    def normalized_key(self) -> str:
        """Return normalized (artist + title) key for deduplication."""
        return normalize_track_string(f"{self.primary_artist} {self.title}")

    @property
    def safe_filename_base(self) -> str:
        """Return a filesystem-safe filename base without extension."""
        name = f"{self.primary_artist} - {self.title}"
        # Replace forbidden filesystem characters
        safe = re.sub(r'[\\/*?:"<>|]', "", name)
        # Collapse whitespace
        safe = re.sub(r"\s+", " ", safe).strip()
        return safe or "track"


def normalize_track_string(text: str) -> str:
    """Normalize text by stripping punctuation, bracketed tags (feat, official audio), and casing."""
    text = text.lower()
    # Remove common filler tags like (Official Video), [Audio], (Official Music Video), etc.
    text = re.sub(
        r"[\(\[](official\s+)?(video|audio|music\s+video|lyric\s+video|visualizer)[\)\]]",
        "",
        text,
    )
    # Remove parenthesized / bracketed feat / ft variations: (feat. ...), [ft. ...]
    text = re.sub(r"[\(\[](feat\.?|ft\.?)\s+[^\)\]]+[\)\]]", "", text)
    # Remove unparenthesized feat / ft variations up to next delimiter (e.g., "Drake feat. Wizkid - Song")
    text = re.sub(r"\s+(feat\.?|ft\.?)\s+[^-\(\]]+(?=\s*-\s*|$)", "", text)
    # Strip non-alphanumeric (keep spaces)
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


class DuplicateMatch(BaseModel):
    """Result of duplicate check."""

    is_duplicate: bool
    matched_file_path: Path | None = None
    match_reason: str | None = None
    existing_tags: dict[str, Any] = Field(default_factory=dict)


class DownloadStatus(str, Enum):
    """Status of track processing."""

    SUCCESS = "success"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FORCE_OVERWRITTEN = "force_overwritten"
    FAILED = "failed"


class DownloadResult(BaseModel):
    """Outcome of attempting to download/process a track."""

    track: TrackInfo
    status: DownloadStatus
    output_path: Path | None = None
    duplicate_info: DuplicateMatch | None = None
    error_message: str | None = None
