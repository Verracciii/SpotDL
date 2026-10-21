"""Tests for audio metadata tagging and artwork embedding."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mutagen.id3 import ID3

from dj_downloader.models import TrackInfo
from dj_downloader.tagger import AudioTagger


def test_tag_mp3_file(sample_spotify_track: TrackInfo, tmp_path: Path) -> None:
    test_mp3 = tmp_path / "test_track.mp3"
    test_mp3.touch()

    tagger = AudioTagger()

    with patch("dj_downloader.tagger.fetch_image_bytes", return_value=b"fake_jpeg_data"):
        tagger.tag_file(test_mp3, sample_spotify_track)

    # Read back tags
    tags = ID3(test_mp3)
    assert str(tags.get("TIT2")) == "One Dance"
    assert str(tags.get("TPE1")) == "Drake, Wizkid, Kyla"
    assert str(tags.get("TALB")) == "Views"
    assert str(tags.get("TDRC")) == "2016-04-29"
    assert str(tags.get("TSRC")) == "USCM51600062"
