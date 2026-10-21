"""Tests for URL router."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dj_downloader.models import SourceType, TrackInfo
from dj_downloader.router import classify_url, fetch_tracks


def test_classify_url() -> None:
    assert classify_url("https://open.spotify.com/track/1zi7xxqqst8CR9oxEioOC4") == "spotify"
    assert classify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M") == "spotify"
    assert classify_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert classify_url("https://music.youtube.com/playlist?list=PLrEnWoR732") == "youtube"
    assert classify_url("https://soundcloud.com/artist/track") == "unsupported"


@patch("dj_downloader.spotify.SpotifyExtractor.extract")
def test_fetch_tracks_spotify_route(mock_spotify_extract: MagicMock) -> None:
    mock_spotify_extract.return_value = [
        TrackInfo(
            title="One Dance",
            artists=["Drake"],
            source_url="https://open.spotify.com/track/123",
            source_type=SourceType.SPOTIFY_TRACK,
        )
    ]
    tracks = fetch_tracks("https://open.spotify.com/track/123")
    assert len(tracks) == 1
    assert tracks[0].title == "One Dance"
    mock_spotify_extract.assert_called_once()


@patch("dj_downloader.youtube.YouTubeExtractor.extract")
def test_fetch_tracks_youtube_route(mock_youtube_extract: MagicMock) -> None:
    mock_youtube_extract.return_value = [
        TrackInfo(
            title="Strobe",
            artists=["deadmau5"],
            source_url="https://youtube.com/watch?v=456",
            source_type=SourceType.YOUTUBE_VIDEO,
        )
    ]
    tracks = fetch_tracks("https://youtube.com/watch?v=456")
    assert len(tracks) == 1
    assert tracks[0].title == "Strobe"
    mock_youtube_extract.assert_called_once()


def test_fetch_tracks_unsupported_url() -> None:
    with pytest.raises(ValueError, match="Unsupported URL format"):
        fetch_tracks("https://apple.music.com/album/123")
