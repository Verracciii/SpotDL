"""Unified URL router for Spotify and YouTube links."""

from __future__ import annotations

import re

from dj_downloader.models import TrackInfo
from dj_downloader.spotify import SPOTIFY_URL_PATTERN, SpotifyExtractor
from dj_downloader.youtube import YOUTUBE_URL_PATTERN, YouTubeExtractor


def classify_url(url: str) -> str:
    """Classify input URL into 'spotify', 'youtube', or 'unsupported'."""
    url = url.strip()
    if SPOTIFY_URL_PATTERN.search(url):
        return "spotify"
    if YOUTUBE_URL_PATTERN.search(url) or re.search(r"https?://(?:music\.)?youtube\.com/", url):
        return "youtube"
    return "unsupported"


def fetch_tracks(url: str) -> list[TrackInfo]:
    """Unified entry point to extract TrackInfo items from any supported URL."""
    service = classify_url(url)

    if service == "spotify":
        extractor = SpotifyExtractor()
        return extractor.extract(url)
    elif service == "youtube":
        yt_extractor = YouTubeExtractor()
        return yt_extractor.extract(url)
    else:
        raise ValueError(
            f"Unsupported URL format: '{url}'. Supported services: Spotify (track/album/playlist) "
            "and YouTube / YouTube Music (video/playlist)."
        )
