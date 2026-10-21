"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from dj_downloader.models import SourceType, TrackInfo


@pytest.fixture
def sample_spotify_track() -> TrackInfo:
    return TrackInfo(
        title="One Dance",
        artists=["Drake", "Wizkid", "Kyla"],
        album="Views",
        album_artist="Drake",
        release_date="2016-04-29",
        duration_ms=173986,
        isrc="USCM51600062",
        spotify_id="1zi7xxqqst8CR9oxEioOC4",
        source_url="https://open.spotify.com/track/1zi7xxqqst8CR9oxEioOC4",
        source_type=SourceType.SPOTIFY_TRACK,
        cover_url="https://i.scdn.co/image/ab67616d0000b2739416ed64def84923d9a6b122",
        track_number=12,
        disc_number=1,
    )


@pytest.fixture
def sample_youtube_track() -> TrackInfo:
    return TrackInfo(
        title="Strobe (Radio Edit)",
        artists=["deadmau5"],
        album="For Lack of a Better Name",
        duration_ms=214000,
        source_url="https://www.youtube.com/watch?v=tKi9Z-f6qX4",
        source_type=SourceType.YOUTUBE_VIDEO,
        cover_url="https://i.ytimg.com/vi/tKi9Z-f6qX4/hqdefault.jpg",
    )
