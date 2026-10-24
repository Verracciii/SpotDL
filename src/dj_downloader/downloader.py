"""Audio search matching and downloader powered by yt-dlp."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from dj_downloader.config import settings
from dj_downloader.models import AudioFormat, SourceType, TrackInfo

logger = logging.getLogger(__name__)


def construct_search_queries(track: TrackInfo) -> list[str]:
    """Generate prioritized search queries for locating the best audio stream."""
    if track.source_type in (SourceType.YOUTUBE_VIDEO, SourceType.YOUTUBE_PLAYLIST):
        return [track.source_url]

    queries: list[str] = [
        f"{track.primary_artist} - {track.title} audio",
        f"{track.primary_artist} - {track.title}",
    ]

    if track.isrc:
        queries.append(f"{track.isrc}")

    return queries


def get_cookie_opts(
    cookies_browser: str | None = None,
    cookie_file: Path | None = None,
) -> dict[str, Any]:
    """Generate yt-dlp cookie options from browser or cookie file settings."""
    if cookie_file:
        resolved_path = Path(cookie_file).expanduser().resolve()
        if resolved_path.exists():
            return {"cookiefile": str(resolved_path)}
        logger.warning(f"Configured cookie file does not exist: {cookie_file}")

    if cookies_browser:
        browser_clean = cookies_browser.strip().lower()
        if browser_clean == "auto":
            return {"cookiesfrombrowser": ("chrome",)}
        return {"cookiesfrombrowser": (browser_clean,)}

    return {}


class AudioDownloader:
    """Finds best audio match and extracts high-quality audio streams."""

    def __init__(
        self,
        output_dir: Path | None = None,
        audio_format: AudioFormat = AudioFormat.MP3,
        audio_bitrate: str = "320k",
        max_duration_diff_sec: int = 15,
        cookies_browser: str | None = None,
        cookie_file: Path | None = None,
    ) -> None:
        self.output_dir = output_dir or settings.output_dir
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.max_duration_diff_sec = max_duration_diff_sec
        self.cookies_browser = (
            cookies_browser if cookies_browser is not None else settings.cookies_browser
        )
        self.cookie_file = cookie_file if cookie_file is not None else settings.cookie_file

    def find_best_match(self, track: TrackInfo) -> str | None:
        """Find the matching YouTube stream URL that passes duration verification."""
        if track.source_type in (SourceType.YOUTUBE_VIDEO, SourceType.YOUTUBE_PLAYLIST):
            return track.source_url

        target_duration_sec = track.duration_ms / 1000.0 if track.duration_ms > 0 else None
        search_queries = construct_search_queries(track)

        cookie_opts = get_cookie_opts(self.cookies_browser, self.cookie_file)
        ydl_opts: dict[str, Any] = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch5",
            "extractor_args": {
                "youtube": {
                    "player_client": ["visionos", "mweb", "android"],
                }
            },
            **cookie_opts,
        }

        with YoutubeDL(ydl_opts) as ydl:
            for query in search_queries:
                search_target = f"ytsearch5:{query}"
                try:
                    res = ydl.extract_info(search_target, download=False)
                    if not res or "entries" not in res:
                        continue

                    for entry in res.get("entries", []):
                        if not entry:
                            continue

                        duration = entry.get("duration")
                        if target_duration_sec and duration:
                            diff = abs(duration - target_duration_sec)
                            if diff > self.max_duration_diff_sec:
                                logger.debug(
                                    f"Skipping match '{entry.get('title')}' - duration diff {diff:.1f}s > {self.max_duration_diff_sec}s"
                                )
                                continue

                        url = entry.get("webpage_url") or entry.get("url") or entry.get("id")
                        if url:
                            return (
                                f"https://www.youtube.com/watch?v={url}"
                                if not str(url).startswith("http")
                                else str(url)
                            )

                except Exception as e:
                    logger.debug(f"Search query '{query}' failed: {e}")

        return None

    def download(self, track: TrackInfo, destination_dir: Path | None = None) -> Path:
        """Download and convert track audio to the target format."""
        target_dir = destination_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        stream_url = self.find_best_match(track)
        if not stream_url:
            raise RuntimeError(f"No matching audio stream found for '{track.display_name}'")

        file_stem = track.safe_filename_base
        expected_output = target_dir / f"{file_stem}.{self.audio_format.value}"

        cookie_opts = get_cookie_opts(self.cookies_browser, self.cookie_file)
        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(target_dir / f"{file_stem}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["visionos", "mweb", "android"],
                }
            },
            **cookie_opts,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format.value,
                    "preferredquality": (
                        self.audio_bitrate.rstrip("k")
                        if self.audio_format == AudioFormat.MP3
                        else "0"
                    ),
                }
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([stream_url])

        if expected_output.exists():
            return expected_output

        # Fallback search if extension differed
        candidates = list(target_dir.glob(f"{file_stem}.*"))
        if candidates:
            return candidates[0]

        raise FileNotFoundError(f"Failed to find downloaded audio at {expected_output}")
