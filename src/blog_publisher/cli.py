"""
Command-line interface for blog publisher.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from .core import publish_posts


@click.command()
@click.option(
    "--ready-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing posts ready to publish",
)
@click.option(
    "--published-dir",
    type=click.Path(path_type=Path),
    help="Directory to store published posts",
)
@click.option(
    "--blog-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Blog repository _posts directory",
)
@click.option(
    "--assets-dir",
    type=click.Path(path_type=Path),
    help="Blog repository assets directory for Excalidraw SVGs",
)
@click.option(
    "--svg-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing SVG source files (Excalidraw directory)",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file with default paths",
)
def main(
    ready_dir: Optional[Path],
    published_dir: Optional[Path],
    blog_dir: Optional[Path],
    assets_dir: Optional[Path],
    svg_dir: Optional[Path],
    config_file: Optional[Path],
) -> None:
    """Convert Obsidian notes to Jekyll blog posts."""

    # Try to detect default paths if not provided
    if (
        not ready_dir
        or not published_dir
        or not blog_dir
        or not assets_dir
        or not svg_dir
    ):
        defaults = detect_default_paths()
        ready_dir = ready_dir or defaults.get("ready_dir")
        published_dir = published_dir or defaults.get("published_dir")
        blog_dir = blog_dir or defaults.get("blog_dir")
        assets_dir = assets_dir or defaults.get("assets_dir")
        svg_dir = svg_dir or defaults.get("svg_dir")

    # Validate required paths
    if not ready_dir:
        click.echo(
            "Error: Could not find Ready directory. Please specify --ready-dir",
            err=True,
        )
        sys.exit(1)

    if not published_dir:
        click.echo(
            "Error: Could not determine published directory. Please specify --published-dir",
            err=True,
        )
        sys.exit(1)

    if not blog_dir:
        click.echo(
            "Error: Could not find blog _posts directory. Please specify --blog-dir",
            err=True,
        )
        sys.exit(1)

    try:
        published_files = publish_posts(
            ready_dir, published_dir, blog_dir, assets_dir, svg_dir
        )
        if published_files:
            click.echo(f"\n✅ Successfully published {len(published_files)} post(s)!")
            if assets_dir:
                click.echo(f"📁 Assets directory: {assets_dir}")
            if svg_dir:
                click.echo(f"🎨 SVG source directory: {svg_dir}")
        else:
            click.echo("ℹ️  No posts found to publish.")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def detect_default_paths() -> dict[str, Optional[Path]]:
    """Try to detect default directory paths."""
    cwd = Path.cwd()

    # Look for jelly-brain structure
    potential_paths: dict[str, Optional[Path]] = {
        "ready_dir": None,
        "published_dir": None,
        "blog_dir": None,
        "assets_dir": None,
        "svg_dir": None,
    }

    # Check if we're in jelly-brain repo
    if (cwd / "Blog" / "Ready").exists():
        potential_paths["ready_dir"] = cwd / "Blog" / "Ready"
        potential_paths["published_dir"] = cwd / "Blog" / "Published"

        # Auto-detect Excalidraw/ directory at vault root
        # Vault root is the parent of the Ready/ directory's parent
        vault_root = cwd
        excalidraw_dir = vault_root / "Excalidraw"
        if excalidraw_dir.exists():
            potential_paths["svg_dir"] = excalidraw_dir

    # Look for blog repo (chris-jelly.github.io)
    blog_repo_paths = [
        cwd.parent / "chris-jelly.github.io",
        Path.home() / "git" / "chris-jelly.github.io",
    ]

    for blog_repo_path in blog_repo_paths:
        posts_path = blog_repo_path / "_posts"
        assets_path = blog_repo_path / "assets"

        if posts_path.exists():
            potential_paths["blog_dir"] = posts_path
            if assets_path.exists():
                potential_paths["assets_dir"] = assets_path
            break

    return potential_paths


if __name__ == "__main__":
    main()
