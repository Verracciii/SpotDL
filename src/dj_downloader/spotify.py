"""Spotify metadata extractor."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from dj_downloader.config import settings
from dj_downloader.models import SourceType, TrackInfo

logger = logging.getLogger(__name__)

_LOOKUP_WORKERS = 8

SPOTIFY_URL_PATTERN = re.compile(
    r"https?://open\.spotify\.com/(?P<type>track|album|playlist|artist)/(?P<id>[a-zA-Z0-9]+)"
)

# A minimal UA is deliberate: with a full browser UA, Spotify serves a JS app shell without the
# <meta> tags (og:image, music:album) that the track-page lookup relies on.
_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _get_html(url: str) -> str:
    """Fetch a public Spotify page."""
    resp = requests.get(url, headers=_HTTP_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text


def _meta_content(html: str, key: str) -> str | None:
    """Return the content of a <meta property|name="key"> tag, if present."""
    match = re.search(rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"', html)
    return match.group(1) if match else None


def _best_image_url(entity: dict[str, Any]) -> str | None:
    """Pick the largest cover image from an embed entity (coverArt or visualIdentity)."""
    sources = entity.get("coverArt", {}).get("sources") or entity.get("visualIdentity", {}).get(
        "image"
    )
    if not sources:
        return None
    best = max(sources, key=lambda s: s.get("maxWidth") or s.get("width") or 0)
    url = best.get("url")
    return str(url) if url else None


class SpotifyExtractor:
    """Extracts track metadata from Spotify links."""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = client_id or settings.spotipy_client_id
        self.client_secret = client_secret or settings.spotipy_client_secret
        self._sp: spotipy.Spotify | None = None
        self._album_cache: dict[str, tuple[str | None, str | None]] = {}

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
            try:
                return self._extract_via_api(sp, item_type, item_id, url)
            except Exception as e:
                logger.warning(f"Spotify API error ({e}). Falling back to public embed fetcher...")
                return self._extract_via_embed(item_type, item_id, url)
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

    def _fetch_embed_entity(self, item_type: str, item_id: str) -> dict[str, Any]:
        """Fetch and parse the public embed page entity for a Spotify item."""
        html = _get_html(f"https://open.spotify.com/embed/{item_type}/{item_id}")
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html
        )
        if not match:
            match = re.search(r'<script id="initial-state" type="text/plain">(.*?)</script>', html)
        if not match:
            return {}
        state_data = json.loads(match.group(1))
        entity: dict[str, Any] = (
            state_data.get("props", {})
            .get("pageProps", {})
            .get("state", {})
            .get("data", {})
            .get("entity", {})
        )
        if not entity:
            entity = state_data.get("data", {}).get("entity", {})
        return entity

    def _lookup_track_album(self, track_id: str) -> dict[str, str | None]:
        """Best-effort per-track album name, album artist, cover and release date.

        Playlist embeds carry no per-track album data, so read it from the track's public page.
        """
        info: dict[str, str | None] = {
            "album": None,
            "album_artist": None,
            "cover_url": None,
            "release_date": None,
        }
        try:
            html = _get_html(f"https://open.spotify.com/track/{track_id}")
            info["cover_url"] = _meta_content(html, "og:image")
            info["release_date"] = _meta_content(html, "music:release_date")
            album_url = _meta_content(html, "music:album") or ""
            album_match = SPOTIFY_URL_PATTERN.search(album_url)
            if album_match:
                album_id = album_match.group("id")
                if album_id not in self._album_cache:
                    album_entity = self._fetch_embed_entity("album", album_id)
                    self._album_cache[album_id] = (
                        album_entity.get("title"),
                        album_entity.get("subtitle"),
                    )
                info["album"], info["album_artist"] = self._album_cache[album_id]
        except Exception as e:
            logger.warning(f"Could not look up album for Spotify track {track_id}: {e}")
        return info

    def _extract_via_embed(
        self, item_type: str, item_id: str, original_url: str
    ) -> list[TrackInfo]:
        """Fallback extractor using public Spotify pages when the API is unavailable."""
        tracks: list[TrackInfo] = []
        try:
            entity = self._fetch_embed_entity(item_type, item_id)

            if item_type == "track":
                tracks.append(
                    self._parse_embed_entity(entity, SourceType.SPOTIFY_TRACK, original_url)
                )
            elif item_type in ("album", "playlist"):
                is_playlist = item_type == "playlist"
                container_title = entity.get("title")
                container_cover = _best_image_url(entity)
                source_type = (
                    SourceType.SPOTIFY_PLAYLIST if is_playlist else SourceType.SPOTIFY_ALBUM
                )

                track_items = entity.get("trackList", [])
                infos: dict[str, dict[str, str | None]] = {}
                if is_playlist:
                    # Lookups are independent network calls; run them concurrently.
                    # Two threads may fetch the same album once; the cache write is idempotent.
                    ids = [i["uri"].split(":")[-1] for i in track_items if i.get("uri")]
                    with ThreadPoolExecutor(max_workers=_LOOKUP_WORKERS) as pool:
                        infos = dict(zip(ids, pool.map(self._lookup_track_album, ids), strict=True))

                for item in track_items:
                    artists = [item.get("subtitle", "Unknown Artist")]
                    if "," in artists[0]:
                        artists = [a.strip() for a in artists[0].split(",")]
                    track_id = item.get("uri", "").split(":")[-1] if item.get("uri") else None

                    album: str | None = container_title
                    album_artist: str | None = entity.get("subtitle")
                    cover: str | None = container_cover
                    release_date: str | None = None
                    if is_playlist:
                        # Playlist title/cover must not leak into per-track album tags.
                        info = infos.get(track_id or "", {})
                        album = info.get("album")
                        album_artist = info.get("album_artist")
                        cover = info.get("cover_url")
                        release_date = info.get("release_date")

                    tracks.append(
                        TrackInfo(
                            title=item.get("title", "Unknown Title"),
                            artists=artists,
                            album=album,
                            playlist_name=container_title if is_playlist else None,
                            album_artist=album_artist,
                            release_date=release_date,
                            duration_ms=int(item.get("duration", 0)),
                            spotify_id=track_id,
                            source_url=original_url,
                            source_type=source_type,
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
        """Parse a single-track embed entity and enrich it with album data."""
        title = entity.get("title", "Unknown Title")
        artists = [a["name"] for a in entity.get("artists", []) if a.get("name")]
        if not artists:
            subtitle = entity.get("subtitle")
            artists = [a.strip() for a in subtitle.split(",")] if subtitle else ["Unknown Artist"]
        track_id = entity.get("id")
        info = self._lookup_track_album(track_id) if track_id else {}

        return TrackInfo(
            title=title,
            artists=artists,
            album=info.get("album"),
            album_artist=info.get("album_artist"),
            release_date=info.get("release_date"),
            duration_ms=int(entity.get("duration", 0)),
            spotify_id=track_id,
            source_url=source_url,
            source_type=source_type,
            cover_url=info.get("cover_url") or _best_image_url(entity),
        )
