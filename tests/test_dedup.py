"""Tests for deep recursive directory duplicate detection and indexing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from dj_downloader.dedup import LibraryIndexer
from dj_downloader.models import SourceType, TrackInfo


def test_recursive_directory_scan(tmp_path: Path) -> None:
    # Build nested subdirectories
    sub1 = tmp_path / "House" / "TechHouse"
    sub2 = tmp_path / "Techno" / "PeakTime"
    sub3 = tmp_path / "HipHop"
    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)
    sub3.mkdir(parents=True)

    # Create dummy audio files
    file1 = sub1 / "Fisher - Losing It.mp3"
    file2 = sub2 / "Enrico Sangiuliano - Moon Rocks.flac"
    file3 = sub3 / "Drake - One Dance.m4a"
    file1.touch()
    file2.touch()
    file3.touch()

    # Create a non-audio file (e.g. .DS_Store or album art)
    (sub1 / "artwork.jpg").touch()
    (sub2 / ".DS_Store").touch()

    indexer = LibraryIndexer(root_dir=tmp_path)
    indexed_files = indexer.scan()

    assert len(indexed_files) == 3
    assert file1 in indexer.file_paths
    assert file2 in indexer.file_paths
    assert file3 in indexer.file_paths


def test_duplicate_detection_by_normalized_filename(tmp_path: Path) -> None:
    sub = tmp_path / "Playlists" / "Festival_2024"
    sub.mkdir(parents=True)
    existing_file = sub / "Drake feat. Wizkid - One Dance (Official Audio).mp3"
    existing_file.touch()

    indexer = LibraryIndexer(root_dir=tmp_path)
    indexer.scan()

    incoming_track = TrackInfo(
        title="One Dance",
        artists=["Drake", "Wizkid"],
        source_url="https://open.spotify.com/track/123",
        source_type=SourceType.SPOTIFY_TRACK,
    )

    match = indexer.check_duplicate(incoming_track)
    assert match.is_duplicate is True
    assert match.matched_file_path == existing_file
    assert "Playlists/Festival_2024" in str(match.matched_file_path)


def test_no_false_positive_different_song(tmp_path: Path) -> None:
    sub = tmp_path / "HipHop"
    sub.mkdir(parents=True)
    (sub / "Drake - One Dance.mp3").touch()

    indexer = LibraryIndexer(root_dir=tmp_path)
    indexer.scan()

    different_track = TrackInfo(
        title="Hotline Bling",
        artists=["Drake"],
        source_url="https://open.spotify.com/track/456",
        source_type=SourceType.SPOTIFY_TRACK,
    )

    match = indexer.check_duplicate(different_track)
    assert match.is_duplicate is False
    assert match.matched_file_path is None


@patch("dj_downloader.dedup.read_audio_tags")
def test_duplicate_detection_by_id3_tags(mock_read_tags: MagicMock, tmp_path: Path) -> None:
    music_dir = tmp_path / "Unorganized"
    music_dir.mkdir(parents=True)
    generic_file = music_dir / "track_01_rip.mp3"
    generic_file.touch()

    # Mock tag reader returning embedded metadata
    mock_read_tags.return_value = {
        "artist": "Calvin Harris",
        "title": "Miracle",
        "isrc": "GBARL2300234",
    }

    indexer = LibraryIndexer(root_dir=tmp_path)
    indexer.scan()

    incoming_track = TrackInfo(
        title="Miracle",
        artists=["Calvin Harris", "Ellie Goulding"],
        isrc="GBARL2300234",
        source_url="https://open.spotify.com/track/789",
        source_type=SourceType.SPOTIFY_TRACK,
    )

    match = indexer.check_duplicate(incoming_track)
    assert match.is_duplicate is True
    assert match.matched_file_path == generic_file
