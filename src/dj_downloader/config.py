"""Configuration management for DJ Spotify & YouTube Downloader."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dj_downloader.models import AudioFormat


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Spotify API (Optional - enhances metadata and allows fetching private/large playlists)
    spotipy_client_id: str | None = Field(default=None, alias="SPOTIPY_CLIENT_ID")
    spotipy_client_secret: str | None = Field(default=None, alias="SPOTIPY_CLIENT_SECRET")

    # Downloader settings
    output_dir: Path = Field(default=Path("./downloads"), alias="DJ_DL_OUTPUT_DIR")
    audio_format: AudioFormat = Field(default=AudioFormat.MP3, alias="DJ_DL_AUDIO_FORMAT")
    audio_bitrate: str = Field(default="320k", alias="DJ_DL_AUDIO_BITRATE")

    # Rate limiting & Anti-bot
    min_delay_seconds: float = Field(default=2.0, alias="DJ_DL_MIN_DELAY_SECONDS")
    max_delay_seconds: float = Field(default=5.0, alias="DJ_DL_MAX_DELAY_SECONDS")
    max_retries: int = Field(default=3, alias="DJ_DL_MAX_RETRIES")

    # Duplicate checking
    recursive_scan: bool = Field(default=True, alias="DJ_DL_RECURSIVE_SCAN")
    supported_audio_extensions: tuple[str, ...] = (
        ".mp3",
        ".flac",
        ".m4a",
        ".wav",
        ".aiff",
        ".aif",
        ".ogg",
        ".opus",
    )


settings = Settings()
