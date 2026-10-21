"""Tests for YouTube metadata extractor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dj_downloader.models import SourceType
from dj_downloader.youtube import (
    YOUTUBE_URL_PATTERN,
    YouTubeExtractor,
    parse_youtube_title_and_artist,
)


def test_youtube_url_patterns() -> None:
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PLrEnWoR732-DNpTUS21fL2iS7_Y02pA5e",
        "https://music.youtube.com/playlist?list=PLrEnWoR732-DNpTUS21fL2iS7_Y02pA5e",
    ]
    for url in valid_urls:
        assert YOUTUBE_URL_PATTERN.search(url) is not None


def test_parse_youtube_title_and_artist() -> None:
    # Standard Artist - Title
    artist, title = parse_youtube_title_and_artist("deadmau5 - Strobe (Radio Edit)", "deadmau5 - Topic")
    assert artist == "deadmau5"
    assert title == "Strobe (Radio Edit)"

    # With Official Video tag
    artist, title = parse_youtube_title_and_artist("Fisher - Losing It (Official Video)", "FisherVEVO")
    assert artist == "Fisher"
    assert title == "Losing It"

    # En-dash / Em-dash
    artist, title = parse_youtube_title_and_artist("Peggy Gou – (It Goes Like) Nanana", "Peggy Gou")
    assert artist == "Peggy Gou"
    assert title == "(It Goes Like) Nanana"

    # No dash in title, fallback to uploader/channel
    artist, title = parse_youtube_title_and_artist("Animals", "Martin Garrix")
    assert artist == "Martin Garrix"
    assert title == "Animals"


@patch("dj_downloader.youtube.YoutubeDL")
def test_youtube_extract_single_video(mock_ydl_class: MagicMock) -> None:
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "_type": "video",
        "id": "tKi9Z-f6qX4",
        "title": "deadmau5 - Strobe",
        "uploader": "deadmau5",
        "duration": 214,
        "thumbnail": "https://i.ytimg.com/vi/tKi9Z-f6qX4/hqdefault.jpg",
        "webpage_url": "https://www.youtube.com/watch?v=tKi9Z-f6qX4",
        "album": "For Lack of a Better Name",
    }
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl

    extractor = YouTubeExtractor()
    tracks = extractor.extract("https://www.youtube.com/watch?v=tKi9Z-f6qX4")

    assert len(tracks) == 1
    track = tracks[0]
    assert track.title == "Strobe"
    assert track.artists == ["deadmau5"]
    assert track.duration_ms == 214000
    assert track.source_type == SourceType.YOUTUBE_VIDEO
