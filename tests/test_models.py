"""Tests for data models and track string normalization."""

from __future__ import annotations

from dj_downloader.models import SourceType, TrackInfo, normalize_track_string


def test_normalize_track_string() -> None:
    # Test removing feat / ft tags
    assert (
        normalize_track_string("Drake feat. Wizkid - One Dance")
        == "drake one dance"
    )
    assert (
        normalize_track_string("Calvin Harris (ft. Ellie Goulding) - Miracle")
        == "calvin harris miracle"
    )
    assert (
        normalize_track_string("Tiësto - The Business (Official Music Video)")
        == "tiësto the business"
    )
    assert (
        normalize_track_string("Fisher - Losing It [Official Audio]")
        == "fisher losing it"
    )
    # Punctuation stripping
    assert (
        normalize_track_string("Don't You Worry Child!")
        == "dont you worry child"
    )


def test_track_info_properties(sample_spotify_track: TrackInfo) -> None:
    assert sample_spotify_track.primary_artist == "Drake"
    assert sample_spotify_track.artist_string == "Drake, Wizkid, Kyla"
    assert sample_spotify_track.display_name == "Drake - One Dance"
    assert "drake" in sample_spotify_track.normalized_key
    assert "one dance" in sample_spotify_track.normalized_key
    assert sample_spotify_track.safe_filename_base == "Drake - One Dance"


def test_safe_filename_special_characters() -> None:
    track = TrackInfo(
        title='Song: "What/Why?" <VIP Mix> | *Live*',
        artists=["DJ/Producer?"],
        source_url="https://youtube.com/watch?v=123",
        source_type=SourceType.YOUTUBE_VIDEO,
    )
    assert "/" not in track.safe_filename_base
    assert "?" not in track.safe_filename_base
    assert ":" not in track.safe_filename_base
    assert "<" not in track.safe_filename_base
    assert ">" not in track.safe_filename_base
    assert "|" not in track.safe_filename_base
    assert "*" not in track.safe_filename_base
    assert track.safe_filename_base == "DJProducer - Song WhatWhy VIP Mix Live"
