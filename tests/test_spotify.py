"""Tests for Spotify metadata extractor."""

from __future__ import annotations

from unittest.mock import MagicMock

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


def _embed_html(entity: dict) -> str:  # type: ignore[type-arg]
    import json

    data = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'


def _track_page(cover: str, album_id: str, release: str) -> str:
    return (
        f'<meta property="og:image" content="{cover}"/>'
        f'<meta name="music:album" content="https://open.spotify.com/album/{album_id}"/>'
        f'<meta name="music:release_date" content="{release}"/>'
    )


def test_spotify_embed_playlist_uses_per_track_album_and_cover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = {
        "https://open.spotify.com/embed/playlist/PL1": _embed_html(
            {
                "title": "My Playlist",
                "coverArt": {"sources": [{"url": "https://playlist-cover.jpg"}]},
                "trackList": [
                    {"uri": "spotify:track:T1", "title": "Song One", "subtitle": "Artist A"},
                    {"uri": "spotify:track:T2", "title": "Song Two", "subtitle": "Artist B"},
                ],
            }
        ),
        "https://open.spotify.com/track/T1": _track_page(
            "https://cover-a.jpg", "ALB1", "2020-01-01"
        ),
        "https://open.spotify.com/track/T2": _track_page(
            "https://cover-b.jpg", "ALB2", "2021-02-02"
        ),
        "https://open.spotify.com/embed/album/ALB1": _embed_html(
            {"title": "Album A", "subtitle": "Artist A"}
        ),
        "https://open.spotify.com/embed/album/ALB2": _embed_html(
            {"title": "Album B", "subtitle": "Artist B"}
        ),
    }
    monkeypatch.setattr("dj_downloader.spotify._get_html", lambda url: pages[url])

    extractor = SpotifyExtractor(client_id="", client_secret="")
    tracks = extractor._extract_via_embed("playlist", "PL1", "u")

    assert [t.album for t in tracks] == ["Album A", "Album B"]
    assert [t.cover_url for t in tracks] == ["https://cover-a.jpg", "https://cover-b.jpg"]
    assert all(t.playlist_name == "My Playlist" for t in tracks)
    assert tracks[0].release_date == "2020-01-01"


def test_spotify_embed_album_keeps_album_name_and_cover(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        "https://open.spotify.com/embed/album/ALB1": _embed_html(
            {
                "title": "Album A",
                "subtitle": "Artist A",
                "visualIdentity": {
                    "image": [
                        {"url": "https://small.jpg", "maxWidth": 64},
                        {"url": "https://big.jpg", "maxWidth": 640},
                    ]
                },
                "trackList": [{"uri": "spotify:track:T1", "title": "S", "subtitle": "Artist A"}],
            }
        )
    }
    monkeypatch.setattr("dj_downloader.spotify._get_html", lambda url: pages[url])

    tracks = SpotifyExtractor(client_id="", client_secret="")._extract_via_embed(
        "album", "ALB1", "u"
    )
    assert tracks[0].album == "Album A"
    assert tracks[0].cover_url == "https://big.jpg"
    assert tracks[0].playlist_name is None


def test_spotify_embed_playlist_lookup_failure_does_not_leak_playlist_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str) -> str:
        if "/embed/playlist/" in url:
            return _embed_html(
                {
                    "title": "My Playlist",
                    "coverArt": {"sources": [{"url": "https://playlist-cover.jpg"}]},
                    "trackList": [{"uri": "spotify:track:T1", "title": "S", "subtitle": "A"}],
                }
            )
        raise RuntimeError("boom")

    monkeypatch.setattr("dj_downloader.spotify._get_html", fake_get)
    tracks = SpotifyExtractor(client_id="", client_secret="")._extract_via_embed(
        "playlist", "PL1", "u"
    )
    assert tracks[0].album is None
    assert tracks[0].cover_url is None
