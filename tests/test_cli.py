"""Tests for CLI interface."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from dj_downloader.cli import app
from dj_downloader.models import SourceType, TrackInfo

runner = CliRunner()


def test_cli_config_show() -> None:
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "DJ SpotDL Configuration" in result.output


def test_cli_config_set_library(tmp_path: Path) -> None:
    lib_path = tmp_path / "MyDJLibrary"
    lib_path.mkdir()

    config_file = tmp_path / "test_cfg.json"

    with (
        patch("dj_downloader.cli.DEFAULT_CONFIG_PATH", config_file),
        patch("dj_downloader.config.DEFAULT_CONFIG_PATH", config_file),
    ):
        result = runner.invoke(app, ["config", "set-library", str(lib_path)])
        assert result.exit_code == 0
        assert "Master DJ Library directory updated" in result.output


@patch("dj_downloader.cli.fetch_tracks")
@patch("dj_downloader.cli.AudioDownloader")
@patch("dj_downloader.cli.AudioTagger")
def test_cli_download_command_flow(
    mock_tagger: MagicMock,
    mock_downloader: MagicMock,
    mock_fetch_tracks: MagicMock,
    tmp_path: Path,
) -> None:
    track = TrackInfo(
        title="One Dance",
        artists=["Drake"],
        source_url="https://open.spotify.com/track/123",
        source_type=SourceType.SPOTIFY_TRACK,
    )
    mock_fetch_tracks.return_value = [track]

    mock_dl_instance = MagicMock()
    mock_dl_instance.download.return_value = tmp_path / "Drake - One Dance.mp3"
    mock_downloader.return_value = mock_dl_instance

    result = runner.invoke(
        app,
        [
            "download",
            "https://open.spotify.com/track/123",
            "--output-dir",
            str(tmp_path / "downloads"),
            "--library-dir",
            str(tmp_path / "library"),
        ],
    )

    assert result.exit_code == 0
    assert "Drake - One Dance" in result.output
    mock_fetch_tracks.assert_called_once_with("https://open.spotify.com/track/123")
