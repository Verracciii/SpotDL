"""Command line interface for DJ Spotify & YouTube Downloader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table

from dj_downloader.config import (
    DEFAULT_CONFIG_PATH,
    load_user_config,
    save_user_config,
)
from dj_downloader.dedup import LibraryIndexer
from dj_downloader.downloader import AudioDownloader
from dj_downloader.limiter import RateLimiter
from dj_downloader.models import (
    AudioFormat,
    DownloadResult,
    DownloadStatus,
    TrackInfo,
)
from dj_downloader.router import fetch_tracks
from dj_downloader.tagger import AudioTagger

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(
    name="dj-dl",
    help="High-reliability audio downloader and deduplicator tailored for DJs.",
    add_completion=False,
)
config_app = typer.Typer(help="Manage persistent application configuration.")
app.add_typer(config_app, name="config")


def ensure_library_dir(library_arg: Path | None) -> Path:
    """Ensure DJ library directory is configured, prompting on first run if needed."""
    cfg = load_user_config()
    if library_arg:
        return library_arg.expanduser().resolve()

    if cfg.dj_library_dir and cfg.dj_library_dir.exists():
        return cfg.dj_library_dir

    console.print(
        Panel.fit(
            "[bold cyan]Welcome to DJ SpotDL![/bold cyan]\n"
            "To prevent duplicate downloads across all your crates and folders,\n"
            "please set the path to your [bold yellow]Master DJ Music Library[/bold yellow].",
            border_style="cyan",
        )
    )

    default_guess = str(Path.home() / "Music")
    chosen_path_str = Prompt.ask("Master DJ Library directory", default=default_guess)
    chosen_path = Path(chosen_path_str).expanduser().resolve()
    chosen_path.mkdir(parents=True, exist_ok=True)

    save_user_config("dj_library_dir", chosen_path)
    console.print(f"[green]Saved Master DJ Library to:[/green] [bold]{chosen_path}[/bold]\n")
    return chosen_path


@app.command(name="download")
def download_command(
    url: Annotated[
        str, typer.Argument(help="Spotify or YouTube URL (track, album, playlist, video)")
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir", "-o", help="Target download directory (defaults to ./downloads)"
        ),
    ] = None,
    library_dir: Annotated[
        Path | None,
        typer.Option(
            "--library-dir",
            "-l",
            help="Master DJ Library directory to recursively check for duplicates",
        ),
    ] = None,
    audio_format: Annotated[
        AudioFormat,
        typer.Option("--format", "-f", help="Output audio format (mp3, flac, wav, m4a)"),
    ] = AudioFormat.MP3,
    force: Annotated[
        bool,
        typer.Option("--force", help="Force download and unskip all existing duplicates"),
    ] = False,
    no_organize: Annotated[
        bool,
        typer.Option("--no-organize", help="Do not create a subfolder for playlists/albums"),
    ] = False,
    cookies_browser: Annotated[
        str | None,
        typer.Option(
            "--cookies-browser",
            help="Extract cookies from browser (e.g. chrome, firefox, safari, brave, edge, auto)",
        ),
    ] = None,
    cookie_file: Annotated[
        Path | None,
        typer.Option(
            "--cookie-file",
            help="Path to cookies.txt file for authentication and age-restricted downloads",
        ),
    ] = None,
) -> None:
    """Download tracks from a Spotify or YouTube link, checking for duplicates."""
    active_library_dir = ensure_library_dir(library_dir)
    cfg = load_user_config()
    target_output_root = (output_dir or cfg.output_dir).expanduser().resolve()

    # Step 1: Scan master library for duplicates
    console.print(
        f"[cyan]Scanning DJ library recursively at:[/cyan] [bold]{active_library_dir}[/bold]..."
    )
    indexer = LibraryIndexer(root_dir=active_library_dir)
    indexed_files = indexer.scan()
    console.print(f"[green]Indexed {len(indexed_files)} existing audio tracks.[/green]\n")

    # Step 2: Fetch track metadata
    with console.status("[bold cyan]Fetching metadata from link...[/bold cyan]"):
        try:
            tracks: list[TrackInfo] = fetch_tracks(
                url,
                cookies_browser=cookies_browser or cfg.cookies_browser,
                cookie_file=cookie_file or cfg.cookie_file,
            )
        except Exception as e:
            console.print(f"[bold red]Failed to fetch tracks:[/bold red] {e}")
            raise typer.Exit(code=1) from e

    if not tracks:
        console.print("[yellow]No tracks found at link.[/yellow]")
        return

    console.print(f"[bold green]Found {len(tracks)} track(s) to process.[/bold green]\n")

    # Step 3: Determine subfolder organization for playlists/albums
    destination_dir = target_output_root
    if len(tracks) > 1 and not no_organize:
        # Determine playlist or album name from first track
        subfolder_name = tracks[0].playlist_name or tracks[0].album or "Playlist_Downloads"
        # Sanitize folder name
        safe_subfolder = "".join(
            c for c in subfolder_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        destination_dir = target_output_root / safe_subfolder
        destination_dir.mkdir(parents=True, exist_ok=True)
        console.print(
            f"[blue]Organizing downloads into folder:[/blue] [bold]{destination_dir}[/bold]\n"
        )

    downloader = AudioDownloader(
        output_dir=destination_dir,
        audio_format=audio_format,
        cookies_browser=cookies_browser or cfg.cookies_browser,
        cookie_file=cookie_file or cfg.cookie_file,
    )
    tagger = AudioTagger()
    limiter = RateLimiter()

    results: list[DownloadResult] = []

    # Step 4: Process tracks with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Processing tracks...", total=len(tracks))

        for idx, track in enumerate(tracks, start=1):
            progress.update(
                task_id,
                description=f"[{idx}/{len(tracks)}] [bold]{track.display_name}[/bold]",
            )

            # Check duplicate
            dup_match = indexer.check_duplicate(track)

            if dup_match.is_duplicate and not force:
                results.append(
                    DownloadResult(
                        track=track,
                        status=DownloadStatus.SKIPPED_DUPLICATE,
                        duplicate_info=dup_match,
                    )
                )
                progress.advance(task_id)
                continue

            # Download and tag
            try:
                downloaded_file = downloader.download(track, destination_dir=destination_dir)
                tagger.tag_file(downloaded_file, track)

                status = (
                    DownloadStatus.FORCE_OVERWRITTEN
                    if dup_match.is_duplicate
                    else DownloadStatus.SUCCESS
                )
                results.append(
                    DownloadResult(
                        track=track,
                        status=status,
                        output_path=downloaded_file,
                        duplicate_info=dup_match if dup_match.is_duplicate else None,
                    )
                )

                # Rate limiting delay between downloads
                if idx < len(tracks):
                    limiter.wait()

            except Exception as e:
                logger.error(f"Error downloading {track.display_name}: {e}")
                results.append(
                    DownloadResult(
                        track=track,
                        status=DownloadStatus.FAILED,
                        error_message=str(e),
                    )
                )

            progress.advance(task_id)

    # Step 5: Render Summary Report Table
    _render_summary_table(results)


def _render_summary_table(results: list[DownloadResult]) -> None:
    """Print final summary of completed, skipped, and failed downloads."""
    table = Table(title="Download Run Summary", border_style="cyan")
    table.add_column("Status", justify="center", style="bold")
    table.add_column("Track", style="cyan")
    table.add_column("Details", style="dim")

    downloaded_count = 0
    skipped_count = 0
    failed_count = 0

    for res in results:
        if res.status == DownloadStatus.SUCCESS:
            downloaded_count += 1
            table.add_row(
                "[green]DOWNLOADED[/green]", res.track.display_name, str(res.output_path or "")
            )
        elif res.status == DownloadStatus.FORCE_OVERWRITTEN:
            downloaded_count += 1
            table.add_row(
                "[yellow]UNSKIPPED[/yellow]",
                res.track.display_name,
                "Force downloaded over duplicate",
            )
        elif res.status == DownloadStatus.SKIPPED_DUPLICATE:
            skipped_count += 1
            dup_loc = res.duplicate_info.matched_file_path if res.duplicate_info else "Library"
            table.add_row(
                "[magenta]SKIPPED (DUPLICATE)[/magenta]",
                res.track.display_name,
                f"Found at: {dup_loc}",
            )
        elif res.status == DownloadStatus.FAILED:
            failed_count += 1
            table.add_row(
                "[red]FAILED[/red]",
                res.track.display_name,
                res.error_message or "Unknown error",
            )

    console.print("\n")
    console.print(table)
    console.print(
        f"\n[bold green]✓ Downloaded: {downloaded_count}[/bold green] | "
        f"[bold magenta]⊘ Skipped (Duplicates): {skipped_count}[/bold magenta] | "
        f"[bold red]✗ Failed: {failed_count}[/bold red]\n"
    )


@config_app.command(name="show")
def config_show() -> None:
    """Display active settings and configuration paths."""
    cfg = load_user_config()
    table = Table(title="DJ SpotDL Configuration", border_style="cyan")
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value", style="green")

    table.add_row("Config File", str(DEFAULT_CONFIG_PATH))
    table.add_row("Master DJ Library Directory", str(cfg.dj_library_dir or "Not Set"))
    table.add_row("Default Output Directory", str(cfg.output_dir))
    table.add_row("Default Audio Format", cfg.audio_format.value)
    table.add_row("Audio Bitrate", cfg.audio_bitrate)
    table.add_row("Cookies Browser", cfg.cookies_browser or "Not Set")
    table.add_row("Cookie File", str(cfg.cookie_file or "Not Set"))
    table.add_row(
        "Spotify API Credentials",
        "Configured" if cfg.spotipy_client_id else "Not Set (Using Embed Fallback)",
    )
    console.print(table)


@config_app.command(name="set-cookies-browser")
def config_set_cookies_browser(
    browser: Annotated[
        str,
        typer.Argument(
            help="Browser name to extract cookies from (e.g. chrome, firefox, safari, edge, brave, auto, or 'none' to clear)"
        ),
    ],
) -> None:
    """Permanently update the browser used for extracting cookies."""
    val: str | None = None if browser.lower() in ("none", "clear", "unset") else browser
    save_user_config("cookies_browser", val)
    if val:
        console.print(f"[green]Cookies browser updated permanently to:[/green] [bold]{val}[/bold]")
    else:
        console.print("[green]Cookies browser setting cleared.[/green]")


@config_app.command(name="set-cookie-file")
def config_set_cookie_file(
    path: Annotated[
        Path,
        typer.Argument(help="Path to cookies.txt file (or 'none' to clear)"),
    ],
) -> None:
    """Permanently update the path to a cookies.txt file."""
    if str(path).lower() in ("none", "clear", "unset"):
        save_user_config("cookie_file", None)
        console.print("[green]Cookie file setting cleared.[/green]")
        return

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Cookie file at {resolved} does not currently exist."
        )
    save_user_config("cookie_file", resolved)
    console.print(
        f"[green]Cookie file path updated permanently to:[/green] [bold]{resolved}[/bold]"
    )


@config_app.command(name="set-library")
def config_set_library(
    path: Annotated[Path, typer.Argument(help="Path to Master DJ Library folder")],
) -> None:
    """Permanently update the Master DJ Library folder for duplicate scanning."""
    resolved = path.expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    save_user_config("dj_library_dir", resolved)
    console.print(
        f"[green]Master DJ Library directory updated permanently to:[/green] [bold]{resolved}[/bold]"
    )


@config_app.command(name="set-output")
def config_set_output(
    path: Annotated[Path, typer.Argument(help="Path to default download destination folder")],
) -> None:
    """Permanently update the default download destination folder."""
    resolved = path.expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    save_user_config("output_dir", resolved)
    console.print(
        f"[green]Default output directory updated permanently to:[/green] [bold]{resolved}[/bold]"
    )


@app.command(name="scan")
def scan_library(
    directory: Annotated[
        Path | None,
        typer.Argument(help="Directory to scan (defaults to Master DJ Library)"),
    ] = None,
) -> None:
    """Recursively scan a directory and inspect total audio files and format breakdown."""
    target_dir = ensure_library_dir(directory)
    console.print(
        f"[cyan]Scanning recursive directory tree at:[/cyan] [bold]{target_dir}[/bold]..."
    )

    indexer = LibraryIndexer(root_dir=target_dir)
    files = indexer.scan()

    ext_counts: dict[str, int] = {}
    for f in files:
        ext = f.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    table = Table(title=f"Library Scan Results ({target_dir.name})", border_style="cyan")
    table.add_column("Audio Format", style="bold")
    table.add_column("Count", justify="right", style="green")

    for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
        table.add_row(ext, str(count))

    console.print(table)
    console.print(f"[bold green]Total indexed audio tracks: {len(files)}[/bold green]\n")


if __name__ == "__main__":
    app()
