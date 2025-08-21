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
    '--ready-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help='Directory containing posts ready to publish',
)
@click.option(
    '--published-dir', 
    type=click.Path(path_type=Path),
    help='Directory to store published posts',
)
@click.option(
    '--blog-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path), 
    help='Blog repository _posts directory',
)
@click.option(
    '--config-file',
    type=click.Path(exists=True, path_type=Path),
    help='Configuration file with default paths',
)
def main(
    ready_dir: Optional[Path],
    published_dir: Optional[Path], 
    blog_dir: Optional[Path],
    config_file: Optional[Path]
) -> None:
    """Convert Obsidian notes to Jekyll blog posts."""
    
    # Try to detect default paths if not provided
    if not ready_dir or not published_dir or not blog_dir:
        defaults = detect_default_paths()
        ready_dir = ready_dir or defaults.get('ready_dir')
        published_dir = published_dir or defaults.get('published_dir')
        blog_dir = blog_dir or defaults.get('blog_dir')
    
    # Validate required paths
    if not ready_dir:
        click.echo("Error: Could not find Ready directory. Please specify --ready-dir", err=True)
        sys.exit(1)
        
    if not published_dir:
        click.echo("Error: Could not determine published directory. Please specify --published-dir", err=True)
        sys.exit(1)
        
    if not blog_dir:
        click.echo("Error: Could not find blog _posts directory. Please specify --blog-dir", err=True)
        sys.exit(1)
    
    try:
        published_files = publish_posts(ready_dir, published_dir, blog_dir)
        if published_files:
            click.echo(f"\n✅ Successfully published {len(published_files)} post(s)!")
        else:
            click.echo("ℹ️  No posts found to publish.")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def detect_default_paths() -> dict[str, Optional[Path]]:
    """Try to detect default directory paths."""
    cwd = Path.cwd()
    
    # Look for jelly-brain structure
    potential_paths = {
        'ready_dir': None,
        'published_dir': None, 
        'blog_dir': None,
    }
    
    # Check if we're in jelly-brain repo
    if (cwd / 'Blog' / 'Ready').exists():
        potential_paths['ready_dir'] = cwd / 'Blog' / 'Ready'
        potential_paths['published_dir'] = cwd / 'Blog' / 'Published'
    
    # Look for blog repo (chris-jelly.github.io)
    blog_repo_paths = [
        cwd.parent / 'chris-jelly.github.io' / '_posts',
        Path.home() / 'git' / 'chris-jelly.github.io' / '_posts',
    ]
    
    for path in blog_repo_paths:
        if path.exists():
            potential_paths['blog_dir'] = path
            break
    
    return potential_paths


if __name__ == '__main__':
    main()