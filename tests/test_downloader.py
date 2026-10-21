"""Tests for audio downloader and search matching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from dj_downloader.downloader import AudioDownloader, construct_search_queries
from dj_downloader.models import AudioFormat, SourceType, TrackInfo


def test_construct_search_queries(sample_spotify_track: TrackInfo) -> None:
    queries = construct_search_queries(sample_spotify_track)
    assert len(queries) >= 2
    # Should include artist and title
    assert "Drake - One Dance" in queries[0]
    # Should include ISRC query if available
    assert any("USCM51600062" in q for q in queries)


def test_construct_search_queries_direct_youtube() -> None:
    yt_track = TrackInfo(
        title="Strobe",
        artists=["deadmau5"],
        source_url="https://www.youtube.com/watch?v=tKi9Z-f6qX4",
        source_type=SourceType.YOUTUBE_VIDEO,
    )
    queries = construct_search_queries(yt_track)
    # Direct YouTube link should use direct URL
    assert queries[0] == "https://www.youtube.com/watch?v=tKi9Z-f6qX4"


@patch("dj_downloader.downloader.YoutubeDL")
def test_audio_downloader_duration_check(mock_ydl_class: MagicMock, tmp_path: Path) -> None:
    mock_ydl = MagicMock()
    # Mock search finding a track with wildly wrong duration (e.g. 10 minute live mix vs 3 minute studio track)
    mock_ydl.extract_info.return_value = {
        "entries": [
            {
                "id": "live_mix_id",
                "title": "One Dance (10hr loop)",
                "duration": 600,  # 10 minutes (track is 173 seconds)
                "webpage_url": "https://youtube.com/watch?v=wrong",
            }
        ]
    }
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl

    downloader = AudioDownloader(output_dir=tmp_path, audio_format=AudioFormat.MP3)
    track = TrackInfo(
        title="One Dance",
        artists=["Drake"],
        duration_ms=173986,  # ~174 seconds
        source_url="https://open.spotify.com/track/123",
        source_type=SourceType.SPOTIFY_TRACK,
    )

    best_match = downloader.find_best_match(track)
    # Should reject the 10 minute track as duration difference > max tolerance (15s)
    assert best_match is None
