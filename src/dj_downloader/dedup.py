"""Deep recursive directory scanner and duplicate detection engine for DJ libraries."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mutagen

from dj_downloader.config import settings
from dj_downloader.models import (
    DuplicateMatch,
    TrackInfo,
    normalize_track_string,
)

logger = logging.getLogger(__name__)


def read_audio_tags(file_path: Path) -> dict[str, Any]:
    """Read metadata tags from an audio file using mutagen."""
    tags_dict: dict[str, Any] = {}
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio is not None:
            if "artist" in audio and audio["artist"]:
                tags_dict["artist"] = audio["artist"][0]
            if "title" in audio and audio["title"]:
                tags_dict["title"] = audio["title"][0]
            if "album" in audio and audio["album"]:
                tags_dict["album"] = audio["album"][0]
            if "isrc" in audio and audio["isrc"]:
                tags_dict["isrc"] = audio["isrc"][0]
    except Exception as e:
        logger.debug(f"Could not read tags for {file_path}: {e}")

    return tags_dict


class LibraryIndexer:
    """Recursively scans and indexes DJ library audio files to detect duplicate tracks."""

    def __init__(
        self,
        root_dir: Path | None = None,
        supported_extensions: tuple[str, ...] | None = None,
    ) -> None:
        self.root_dir = root_dir or settings.dj_library_dir or settings.output_dir
        self.supported_extensions = supported_extensions or settings.supported_audio_extensions
        self.file_paths: list[Path] = []
        self._normalized_filename_map: dict[str, Path] = {}
        self._tag_key_map: dict[str, Path] = {}
        self._isrc_map: dict[str, Path] = {}

    def scan(self) -> list[Path]:
        """Recursively scan root directory and build lookup indices."""
        self.file_paths.clear()
        self._normalized_filename_map.clear()
        self._tag_key_map.clear()
        self._isrc_map.clear()

        if not self.root_dir or not self.root_dir.exists():
            logger.info(f"Library directory {self.root_dir} does not exist or not set yet.")
            return []

        # Recursively scan all subdirectories
        for path in self.root_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith(".") or "/." in str(path):
                continue
            if path.suffix.lower() not in self.supported_extensions:
                continue

            self.file_paths.append(path)

            # 1. Index normalized filename (without extension)
            norm_filename = normalize_track_string(path.stem)
            if norm_filename:
                self._normalized_filename_map[norm_filename] = path

            # 2. Index embedded tags
            tags = read_audio_tags(path)
            if tags.get("artist") and tags.get("title"):
                norm_tag = normalize_track_string(f"{tags['artist']} {tags['title']}")
                if norm_tag:
                    self._tag_key_map[norm_tag] = path

            if tags.get("isrc"):
                self._isrc_map[tags["isrc"].upper().strip()] = path

        return self.file_paths

    def check_duplicate(self, track: TrackInfo) -> DuplicateMatch:
        """Check if incoming track already exists in the indexed library."""
        # 1. Match by ISRC if present
        if track.isrc:
            clean_isrc = track.isrc.upper().strip()
            if clean_isrc in self._isrc_map:
                matched_file = self._isrc_map[clean_isrc]
                return DuplicateMatch(
                    is_duplicate=True,
                    matched_file_path=matched_file,
                    match_reason=f"Matched exact ISRC code: {clean_isrc}",
                )

        # 2. Match by embedded tags key
        track_tag_key = track.normalized_key
        if track_tag_key in self._tag_key_map:
            matched_file = self._tag_key_map[track_tag_key]
            return DuplicateMatch(
                is_duplicate=True,
                matched_file_path=matched_file,
                match_reason=f"Matched ID3 tags: '{track.display_name}'",
            )

        # 3. Match by normalized filename
        if track_tag_key in self._normalized_filename_map:
            matched_file = self._normalized_filename_map[track_tag_key]
            return DuplicateMatch(
                is_duplicate=True,
                matched_file_path=matched_file,
                match_reason=f"Matched filename: '{track.display_name}'",
            )

        # 4. Partial / Fuzzy containment check (Normalized Artist AND Normalized Title present)
        norm_artist = normalize_track_string(track.primary_artist)
        norm_title = normalize_track_string(track.title)

        if norm_artist and norm_title:
            for indexed_name, path in self._normalized_filename_map.items():
                if norm_artist in indexed_name and norm_title in indexed_name:
                    return DuplicateMatch(
                        is_duplicate=True,
                        matched_file_path=path,
                        match_reason=f"Fuzzy matched existing track: '{path.name}'",
                    )

        return DuplicateMatch(is_duplicate=False)
