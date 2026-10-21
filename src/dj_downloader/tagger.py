"""DJ audio metadata tagger and cover artwork injector."""

from __future__ import annotations

import logging
from pathlib import Path

import mutagen
import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    TSRC,
    ID3NoHeaderError,
)
from mutagen.mp4 import MP4, MP4Cover

from dj_downloader.models import TrackInfo

logger = logging.getLogger(__name__)


def fetch_image_bytes(url: str) -> bytes | None:
    """Download image data from URL."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        logger.warning(f"Failed to download artwork from {url}: {e}")
    return None


class AudioTagger:
    """Writes DJ metadata (ID3v2.4 / Vorbis / MP4) and embeds artwork."""

    def tag_file(self, file_path: Path, track: TrackInfo) -> None:
        """Apply track metadata and artwork to file based on its extension."""
        ext = file_path.suffix.lower()

        cover_data: bytes | None = None
        if track.cover_url:
            cover_data = fetch_image_bytes(track.cover_url)

        if ext == ".mp3":
            self._tag_mp3(file_path, track, cover_data)
        elif ext == ".flac":
            self._tag_flac(file_path, track, cover_data)
        elif ext in (".m4a", ".mp4"):
            self._tag_mp4(file_path, track, cover_data)
        else:
            logger.info(
                f"Tagging not specifically implemented for format {ext}, writing generic tags."
            )
            self._tag_generic(file_path, track)

    def _tag_mp3(self, file_path: Path, track: TrackInfo, cover_data: bytes | None) -> None:
        """Tag MP3 file with ID3v2.4 tags."""
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        # Title
        tags["TIT2"] = TIT2(encoding=3, text=track.title)
        # Artist
        tags["TPE1"] = TPE1(encoding=3, text=track.artist_string)

        # Album
        if track.album:
            tags["TALB"] = TALB(encoding=3, text=track.album)

        # Album Artist
        if track.album_artist or track.primary_artist:
            tags["TPE2"] = TPE2(encoding=3, text=track.album_artist or track.primary_artist)

        # Year / Release Date
        if track.release_date:
            tags["TDRC"] = TDRC(encoding=3, text=track.release_date)

        # Track Number
        if track.track_number:
            tags["TRCK"] = TRCK(encoding=3, text=str(track.track_number))

        # Disc Number
        if track.disc_number:
            tags["TPOS"] = TPOS(encoding=3, text=str(track.disc_number))

        # ISRC
        if track.isrc:
            tags["TSRC"] = TSRC(encoding=3, text=track.isrc)

        # Cover Artwork
        if cover_data:
            mime = "image/png" if cover_data.startswith(b"\x89PNG") else "image/jpeg"
            tags["APIC"] = APIC(
                encoding=3,
                mime=mime,
                type=3,  # Cover (front)
                desc="Front Cover",
                data=cover_data,
            )

        tags.save(file_path, v2_version=4)

    def _tag_flac(self, file_path: Path, track: TrackInfo, cover_data: bytes | None) -> None:
        """Tag FLAC file with Vorbis comments and Picture block."""
        audio = FLAC(file_path)
        audio["TITLE"] = track.title
        audio["ARTIST"] = track.artists or [track.primary_artist]
        if track.album:
            audio["ALBUM"] = track.album
        if track.album_artist:
            audio["ALBUMARTIST"] = track.album_artist
        if track.release_date:
            audio["DATE"] = track.release_date
        if track.track_number:
            audio["TRACKNUMBER"] = str(track.track_number)
        if track.isrc:
            audio["ISRC"] = track.isrc

        if cover_data:
            pic = Picture()
            pic.type = 3
            pic.mime = "image/png" if cover_data.startswith(b"\x89PNG") else "image/jpeg"
            pic.data = cover_data
            audio.clear_pictures()
            audio.add_picture(pic)

        audio.save()

    def _tag_mp4(self, file_path: Path, track: TrackInfo, cover_data: bytes | None) -> None:
        """Tag M4A / MP4 container."""
        audio = MP4(file_path)
        audio["\xa9nam"] = track.title
        audio["\xa9ART"] = track.artist_string
        if track.album:
            audio["\xa9alb"] = track.album
        if track.album_artist:
            audio["aART"] = track.album_artist
        if track.release_date:
            audio["\xa9day"] = track.release_date
        if track.track_number:
            audio["trkn"] = [(track.track_number, 0)]

        if cover_data:
            image_format = (
                MP4Cover.FORMAT_PNG if cover_data.startswith(b"\x89PNG") else MP4Cover.FORMAT_JPEG
            )
            audio["covr"] = [MP4Cover(cover_data, imageformat=image_format)]

        audio.save()

    def _tag_generic(self, file_path: Path, track: TrackInfo) -> None:
        """Fallback easy tagger."""
        audio = mutagen.File(file_path, easy=True)
        if audio is not None:
            audio["title"] = track.title
            audio["artist"] = track.artist_string
            if track.album:
                audio["album"] = track.album
            audio.save()
