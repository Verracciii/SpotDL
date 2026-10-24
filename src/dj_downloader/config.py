"""Configuration management and persistent user settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dj_downloader.models import AudioFormat

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "dj-spotdl" / "config.json"


class Settings(BaseSettings):
    """Application settings with environment variable and JSON config support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Highest-level DJ Library Root (scanned recursively for duplicate checks)
    dj_library_dir: Path | None = Field(default=None, alias="DJ_LIBRARY_DIR")

    # Default download destination (defaults to ./downloads in project)
    output_dir: Path = Field(default=Path("./downloads"), alias="DJ_DL_OUTPUT_DIR")

    # Spotify API (Optional - for private/large playlists and richer metadata)
    spotipy_client_id: str | None = Field(default=None, alias="SPOTIPY_CLIENT_ID")
    spotipy_client_secret: str | None = Field(default=None, alias="SPOTIPY_CLIENT_SECRET")

    # Audio quality settings
    audio_format: AudioFormat = Field(default=AudioFormat.MP3, alias="DJ_DL_AUDIO_FORMAT")
    audio_bitrate: str = Field(default="320k", alias="DJ_DL_AUDIO_BITRATE")

    # Rate limiting & Anti-bot protection
    min_delay_seconds: float = Field(default=2.0, alias="DJ_DL_MIN_DELAY_SECONDS")
    max_delay_seconds: float = Field(default=5.0, alias="DJ_DL_MAX_DELAY_SECONDS")
    max_retries: int = Field(default=3, alias="DJ_DL_MAX_RETRIES")

    # Cookies & Authentication
    cookies_browser: str | None = Field(default=None, alias="DJ_DL_COOKIES_BROWSER")
    cookie_file: Path | None = Field(default=None, alias="DJ_DL_COOKIE_FILE")

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


def get_stored_json_config(config_path: Path | None = None) -> dict[str, Any]:
    """Read stored user config from JSON file if exists."""
    target_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    if target_path.is_file():
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"Failed to read user config at {target_path}: {e}")
    return {}


def load_user_config(config_path: Path | None = None) -> Settings:
    """Load settings merging defaults, JSON config file, and env variables."""
    target_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    stored_data = get_stored_json_config(target_path)
    base_settings = Settings()

    if "dj_library_dir" in stored_data and stored_data["dj_library_dir"]:
        base_settings.dj_library_dir = Path(stored_data["dj_library_dir"]).expanduser().resolve()
    if "output_dir" in stored_data and stored_data["output_dir"]:
        base_settings.output_dir = Path(stored_data["output_dir"]).expanduser().resolve()
    if "audio_format" in stored_data and stored_data["audio_format"]:
        base_settings.audio_format = AudioFormat(stored_data["audio_format"])
    if "audio_bitrate" in stored_data and stored_data["audio_bitrate"]:
        base_settings.audio_bitrate = str(stored_data["audio_bitrate"])
    if "cookies_browser" in stored_data and stored_data["cookies_browser"]:
        base_settings.cookies_browser = str(stored_data["cookies_browser"])
    if "cookie_file" in stored_data and stored_data["cookie_file"]:
        base_settings.cookie_file = Path(stored_data["cookie_file"]).expanduser().resolve()

    return base_settings


def save_user_config(key: str, value: Any, config_path: Path | None = None) -> dict[str, Any]:
    """Save or update a setting permanently in the JSON config file."""
    target_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    current_data = get_stored_json_config(target_path)
    current_data[key] = str(value) if isinstance(value, Path) else value
    target_path.write_text(json.dumps(current_data, indent=2), encoding="utf-8")
    return current_data


# Default active settings instance
settings = load_user_config()
