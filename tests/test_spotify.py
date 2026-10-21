"""Tests for Spotify metadata extractor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dj_downloader.models import SourceType
from dj_downloader.spotify import SPOTIFY_URL_PATTERN, SpotifyExtractor


def test_spotify_url_pattern() -> None:
    track_url = "https://open.spotify.com/track/1zi7xxqqst8CR9oxEioOC4?si=123"
    match = SPOTIFY_URL_PATTERN.search(track_url)
    assert match is not None
    assert match.group("type") == "track"
    assert match.group("id") == "1zi7xxqqst8CR9oxEioOC4"

    playlist_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    match = SPOTIFY_URL_PATTERN.search(playlist_url)
    assert match is not None
    assert match.group("type") == "playlist"
    assert match.group("id") == "37i9dQZF1DXcBWIGoYBM5M"

    album_url = "https://open.spotify.com/album/40GMAhriYrtKVChe49HG2L"
    match = SPOTIFY_URL_PATTERN.search(album_url)
    assert match is not None
    assert match.group("type") == "album"
    assert match.group("id") == "40GMAhriYrtKVChe49HG2L"


def test_spotify_extract_invalid_url() -> None:
    extractor = SpotifyExtractor()
    with pytest.raises(ValueError, match="Invalid Spotify URL"):
        extractor.extract("https://not-spotify.com/something")


def test_spotify_extract_api_track() -> None:
    extractor = SpotifyExtractor(client_id="mock_id", client_secret="mock_secret")
    mock_sp = MagicMock()
    mock_sp.track.return_value = {
        "name": "One Dance",
        "artists": [{"name": "Drake"}, {"name": "Wizkid"}],
        "album": {
            "name": "Views",
            "release_date": "2016-04-29",
            "images": [{"url": "https://cover.jpg"}],
            "artists": [{"name": "Drake"}],
        },
        "duration_ms": 173986,
        "external_ids": {"isrc": "USCM51600062"},
        "id": "1zi7xxqqst8CR9oxEioOC4",
        "track_number": 12,
        "disc_number": 1,
    }
    extractor._sp = mock_sp

    tracks = extractor.extract("https://open.spotify.com/track/1zi7xxqqst8CR9oxEioOC4")
    assert len(tracks) == 1
    track = tracks[0]
    assert track.title == "One Dance"
    assert track.artists == ["Drake", "Wizkid"]
    assert track.album == "Views"
    assert track.isrc == "USCM51600062"
    assert track.source_type == SourceType.SPOTIFY_TRACK


def test_spotify_extract_api_playlist_pagination() -> None:
    extractor = SpotifyExtractor(client_id="mock_id", client_secret="mock_secret")
    mock_sp = MagicMock()

    # Page 1
    page1 = {
        "items": [
            {
                "track": {
                    "id": "track1",
                    "name": "Track One",
                    "artists": [{"name": "Artist A"}],
                    "album": {"name": "Album A", "images": []},
                    "duration_ms": 120000,
                    "is_local": False,
                }
            }
        ],
        "next": "page2_url",
    }
    # Page 2
    page2 = {
        "items": [
            {
                "track": {
                    "id": "track2",
                    "name": "Track Two",
                    "artists": [{"name": "Artist B"}],
                    "album": {"name": "Album B", "images": []},
                    "duration_ms": 180000,
                    "is_local": False,
                }
            }
        ],
        "next": None,
    }

    mock_sp.playlist_items.return_value = page1
    mock_sp.next.return_value = page2
    extractor._sp = mock_sp

    tracks = extractor.extract("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
    assert len(tracks) == 2
    assert tracks[0].title == "Track One"
    assert tracks[1].title == "Track Two"
    assert tracks[0].source_type == SourceType.SPOTIFY_PLAYLIST
