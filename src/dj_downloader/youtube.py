"""YouTube & YouTube Music metadata extractor."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from dj_downloader.config import settings
from dj_downloader.downloader import get_cookie_opts, get_js_runtime_opts
from dj_downloader.models import SourceType, TrackInfo

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = re.compile(
    r"https?://(?:(?:www|m|music)\.)?(?:youtube\.com/(?:watch\?v=|playlist\?list=|embed/|shorts/)|youtu\.be/)(?P<id>[a-zA-Z0-9_-]+)"
)


def parse_youtube_title_and_artist(raw_title: str, uploader: str = "") -> tuple[str, str]:
    """Parse raw YouTube video title and channel/uploader into clean (artist, title)."""
    # Clean topic suffix from YouTube Music automated topic channels (e.g. "deadmau5 - Topic" -> "deadmau5")
    uploader = re.sub(r"\s*-\s*Topic$", "", uploader, flags=re.IGNORECASE).strip()
    uploader = re.sub(r"VEVO$", "", uploader, flags=re.IGNORECASE).strip()

    title = raw_title

    # Remove standard noise suffixes: (Official Music Video), [Official Audio], etc.
    title = re.sub(
        r"[\(\[](official\s+)?(video|music\s+video|audio|lyric\s+video|visualizer|hd|hq|4k)[\)\]]",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    # Look for common delimiters separating Artist and Title: " - ", " – ", " — ", " : ", " | "
    delimiter_match = re.search(r"\s+[-–—|~]\s+", title)
    if delimiter_match:
        parts = re.split(r"\s+[-–—|~]\s+", title, maxsplit=1)
        artist_part = parts[0].strip()
        title_part = parts[1].strip()
        return artist_part, title_part

    # If no delimiter found in title, use uploader as artist (if available) and cleaned title as track title
    artist = uploader if uploader else "Unknown Artist"
    return artist, title


class YouTubeExtractor:
    """Extracts track metadata from YouTube and YouTube Music URLs using yt-dlp."""

    def __init__(
        self,
        ydl_opts: dict[str, Any] | None = None,
        cookies_browser: str | None = None,
        cookie_file: Path | None = None,
    ) -> None:
        cookie_opts = get_cookie_opts(
            cookies_browser if cookies_browser is not None else settings.cookies_browser,
            cookie_file if cookie_file is not None else settings.cookie_file,
        )
        js_opts = get_js_runtime_opts()
        default_opts: dict[str, Any] = {
            "extract_flat": "in_playlist",
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            **js_opts,
            **cookie_opts,
        }
        if ydl_opts:
            default_opts.update(ydl_opts)
        self.ydl_opts = default_opts

    def extract(self, url: str) -> list[TrackInfo]:
        """Extract track info from a YouTube video or playlist URL."""
        if not YOUTUBE_URL_PATTERN.search(url):
            raise ValueError(f"Invalid YouTube URL: {url}")

        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                raise RuntimeError(f"Failed to fetch YouTube metadata from {url}: {e}") from e

        if not info:
            return []

        tracks: list[TrackInfo] = []
        info_type = info.get("_type", "video")

        if info_type == "playlist" or "entries" in info:
            entries = info.get("entries", [])
            for entry in entries:
                if entry:
                    track = self._parse_entry(entry, SourceType.YOUTUBE_PLAYLIST, url)
                    if track:
                        tracks.append(track)
        else:
            track = self._parse_entry(info, SourceType.YOUTUBE_VIDEO, url)
            if track:
                tracks.append(track)

        return tracks

    def _parse_entry(
        self, entry: dict[str, Any], source_type: SourceType, original_url: str
    ) -> TrackInfo | None:
        """Parse yt-dlp info dict entry into TrackInfo."""
        raw_title = entry.get("title")
        if not raw_title:
            return None

        uploader = entry.get("uploader") or entry.get("channel") or ""
        artist, title = parse_youtube_title_and_artist(raw_title, uploader)

        # Prefer explicit artist/track metadata if available from YouTube Music
        if entry.get("artist"):
            artist = entry["artist"]
        if entry.get("track"):
            title = entry["track"]

        duration_sec = entry.get("duration") or 0
        duration_ms = int(duration_sec * 1000)

        # Thumbnail / artwork
        thumbnails = entry.get("thumbnails", [])
        cover_url = entry.get("thumbnail")
        if not cover_url and thumbnails:
            cover_url = thumbnails[-1].get("url")

        track_url = entry.get("webpage_url") or entry.get("url") or original_url
        if track_url and not track_url.startswith("http"):
            track_url = f"https://www.youtube.com/watch?v={track_url}"

        artists = [a.strip() for a in re.split(r"[,&/]", artist) if a.strip()]
        if not artists:
            artists = ["Unknown Artist"]

        return TrackInfo(
            title=title,
            artists=artists,
            album=entry.get("album"),
            release_date=entry.get("release_date") or entry.get("upload_date"),
            duration_ms=duration_ms,
            source_url=track_url,
            source_type=source_type,
            cover_url=cover_url,
            extra_metadata={"yt_id": entry.get("id")},
        )
