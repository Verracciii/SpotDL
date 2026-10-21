"""Spotify metadata extractor."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from dj_downloader.config import settings
from dj_downloader.models import SourceType, TrackInfo

logger = logging.getLogger(__name__)

SPOTIFY_URL_PATTERN = re.compile(
    r"https?://open\.spotify\.com/(?P<type>track|album|playlist|artist)/(?P<id>[a-zA-Z0-9]+)"
)


class SpotifyExtractor:
    """Extracts track metadata from Spotify links."""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = client_id or settings.spotipy_client_id
        self.client_secret = client_secret or settings.spotipy_client_secret
        self._sp: spotipy.Spotify | None = None

    def _get_spotify_client(self) -> spotipy.Spotify | None:
        """Initialize authenticated Spotipy client if credentials exist."""
        if self._sp is not None:
            return self._sp

        if self.client_id and self.client_secret:
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
                self._sp = spotipy.Spotify(auth_manager=auth_manager)
                return self._sp
            except Exception as e:
                logger.warning(
                    f"Failed to authenticate with Spotify API: {e}. Falling back to public embed fetcher."
                )

        return None

    def extract(self, url: str) -> list[TrackInfo]:
        """Extract tracks from any supported Spotify URL."""
        match = SPOTIFY_URL_PATTERN.search(url)
        if not match:
            raise ValueError(f"Invalid Spotify URL: {url}")

        item_type = match.group("type")
        item_id = match.group("id")

        sp = self._get_spotify_client()
        if sp:
            return self._extract_via_api(sp, item_type, item_id, url)
        else:
            return self._extract_via_embed(item_type, item_id, url)

    def _extract_via_api(
        self, sp: spotipy.Spotify, item_type: str, item_id: str, original_url: str
    ) -> list[TrackInfo]:
        """Extract metadata using authenticated Spotify Web API with pagination."""
        tracks: list[TrackInfo] = []

        if item_type == "track":
            track_data = sp.track(item_id)
            if track_data:
                tracks.append(
                    self._parse_api_track(track_data, SourceType.SPOTIFY_TRACK, original_url)
                )

        elif item_type == "album":
            album_data = sp.album(item_id)
            album_name = album_data.get("name")
            release_date = album_data.get("release_date")
            cover_url = (
                album_data.get("images", [{}])[0].get("url") if album_data.get("images") else None
            )

            results = album_data.get("tracks", {})
            while results:
                for item in results.get("items", []):
                    tracks.append(
                        self._parse_api_track(
                            item,
                            SourceType.SPOTIFY_ALBUM,
                            original_url,
                            album_name=album_name,
                            release_date=release_date,
                            cover_url=cover_url,
                        )
                    )
                if results.get("next"):
                    results = sp.next(results)
                else:
                    break

        elif item_type == "playlist":
            results = sp.playlist_items(item_id)
            while results:
                for item in results.get("items", []):
                    track = item.get("track")
                    if track and not track.get("is_local") and track.get("id"):
                        tracks.append(
                            self._parse_api_track(track, SourceType.SPOTIFY_PLAYLIST, original_url)
                        )
                if results.get("next"):
                    results = sp.next(results)
                else:
                    break

        elif item_type == "artist":
            top_tracks = sp.artist_top_tracks(item_id)
            for track in top_tracks.get("tracks", []):
                tracks.append(self._parse_api_track(track, SourceType.SPOTIFY_TRACK, original_url))

        return tracks

    def _parse_api_track(
        self,
        data: dict[str, Any],
        source_type: SourceType,
        source_url: str,
        album_name: str | None = None,
        release_date: str | None = None,
        cover_url: str | None = None,
    ) -> TrackInfo:
        """Parse raw Spotipy track dict into TrackInfo model."""
        album = data.get("album", {})
        if not album_name and album:
            album_name = album.get("name")
        if not release_date and album:
            release_date = album.get("release_date")
        if not cover_url and album and album.get("images"):
            cover_url = album["images"][0].get("url")

        artists = [a.get("name", "") for a in data.get("artists", []) if a.get("name")]
        if not artists:
            artists = ["Unknown Artist"]

        isrc = data.get("external_ids", {}).get("isrc")

        return TrackInfo(
            title=data.get("name", "Unknown Title"),
            artists=artists,
            album=album_name,
            album_artist=album.get("artists", [{}])[0].get("name") if album else artists[0],
            release_date=release_date,
            duration_ms=data.get("duration_ms", 0),
            isrc=isrc,
            spotify_id=data.get("id"),
            source_url=source_url,
            source_type=source_type,
            cover_url=cover_url,
            track_number=data.get("track_number"),
            disc_number=data.get("disc_number"),
        )

    def _extract_via_embed(
        self, item_type: str, item_id: str, original_url: str
    ) -> list[TrackInfo]:
        """Fallback extractor using Spotify embed page/token when no API credentials are provided."""
        embed_url = f"https://open.spotify.com/embed/{item_type}/{item_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(embed_url, headers=headers, timeout=10)
        resp.raise_for_status()

        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text
        )
        if not match:
            match = re.search(
                r'<script id="initial-state" type="text/plain">(.*?)</script>', resp.text
            )

        tracks: list[TrackInfo] = []
        if match:
            try:
                state_data = json.loads(match.group(1))
                entity = (
                    state_data.get("props", {})
                    .get("pageProps", {})
                    .get("state", {})
                    .get("data", {})
                    .get("entity", {})
                )
                if not entity:
                    entity = state_data.get("data", {}).get("entity", {})

                if item_type == "track":
                    tracks.append(
                        self._parse_embed_entity(entity, SourceType.SPOTIFY_TRACK, original_url)
                    )
                elif item_type in ("album", "playlist"):
                    track_list = entity.get("trackList", [])
                    album_title = entity.get("title")
                    cover = entity.get("coverArt", {}).get("sources", [{}])[-1].get("url")

                    for item in track_list:
                        artists = [item.get("subtitle", "Unknown Artist")]
                        if "," in artists[0]:
                            artists = [a.strip() for a in artists[0].split(",")]

                        tracks.append(
                            TrackInfo(
                                title=item.get("title", "Unknown Title"),
                                artists=artists,
                                album=album_title,
                                duration_ms=int(item.get("duration", 0)),
                                spotify_id=(
                                    item.get("uri", "").split(":")[-1] if item.get("uri") else None
                                ),
                                source_url=original_url,
                                source_type=(
                                    SourceType.SPOTIFY_PLAYLIST
                                    if item_type == "playlist"
                                    else SourceType.SPOTIFY_ALBUM
                                ),
                                cover_url=cover,
                            )
                        )
            except Exception as e:
                logger.error(f"Error parsing Spotify embed json: {e}")

        if not tracks:
            raise RuntimeError(
                f"Could not extract tracks from Spotify link {original_url}. "
                "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in .env for full API access."
            )

        return tracks

    def _parse_embed_entity(
        self, entity: dict[str, Any], source_type: SourceType, source_url: str
    ) -> TrackInfo:
        """Parse embed entity dictionary."""
        title = entity.get("title", "Unknown Title")
        subtitle = entity.get("subtitle", "Unknown Artist")
        artists = [a.strip() for a in subtitle.split(",")] if subtitle else ["Unknown Artist"]
        cover_sources = entity.get("coverArt", {}).get("sources", [])
        cover_url = cover_sources[-1].get("url") if cover_sources else None

        return TrackInfo(
            title=title,
            artists=artists,
            album=entity.get("title") if source_type == SourceType.SPOTIFY_ALBUM else None,
            duration_ms=int(entity.get("duration", 0)),
            spotify_id=entity.get("id"),
            source_url=source_url,
            source_type=source_type,
            cover_url=cover_url,
        )
