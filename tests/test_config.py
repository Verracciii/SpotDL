"""Tests for configuration and persistent settings manager."""

from __future__ import annotations

import json
from pathlib import Path

from dj_downloader.config import (
    Settings,
    load_user_config,
    save_user_config,
)


def test_default_config_paths() -> None:
    settings = Settings()
    # Default output dir inside project
    assert settings.output_dir == Path("./downloads")
    # Default audio format and bitrate
    assert settings.audio_format == "mp3"
    assert settings.audio_bitrate == "320k"


def test_save_and_load_user_config(tmp_path: Path) -> None:
    test_config_file = tmp_path / "config.json"

    # Save a library directory permanently
    save_user_config(
        "dj_library_dir",
        str(tmp_path / "DJ_Library"),
        config_path=test_config_file,
    )

    # Verify file was written
    assert test_config_file.exists()
    data = json.loads(test_config_file.read_text(encoding="utf-8"))
    assert data["dj_library_dir"] == str(tmp_path / "DJ_Library")

    # Load into settings
    settings = load_user_config(config_path=test_config_file)
    assert settings.dj_library_dir == tmp_path / "DJ_Library"


def test_save_custom_output_dir(tmp_path: Path) -> None:
    test_config_file = tmp_path / "config.json"

    save_user_config(
        "output_dir",
        str(tmp_path / "CustomDownloads"),
        config_path=test_config_file,
    )

    settings = load_user_config(config_path=test_config_file)
    assert settings.output_dir == tmp_path / "CustomDownloads"
