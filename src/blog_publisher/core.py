"""
Core functionality for converting Obsidian notes to Jekyll blog posts.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def generate_slug(title: str) -> str:
    """Generate a Jekyll-compatible URL slug from a post title.

    Args:
        title: The post title

    Returns:
        A URL-safe slug matching Jekyll's :title parameter behavior
    """
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def build_post_registry(posts_dir: Path, ready_files: list[Path]) -> dict[str, str]:
    """Build a registry mapping post titles to their URL slugs.

    Scans the blog's _posts/ directory and current Ready/ batch files to extract
    titles from frontmatter and build a lowercase_title -> slug mapping for
    cross-post link resolution.

    Args:
        posts_dir: Path to the blog's _posts/ directory
        ready_files: List of markdown files in the current Ready/ batch

    Returns:
        Dictionary mapping lowercase titles to URL slugs

    Edge cases:
        - Files without title frontmatter are skipped
        - Duplicate titles: most recent post wins (based on file modification time)
        - Empty directories: returns empty dict
    """
    registry: dict[str, str] = {}

    # Helper to process a file and add to registry
    def add_to_registry(file_path: Path) -> None:
        try:
            frontmatter, _ = extract_frontmatter_and_content(file_path)
            title = frontmatter.get("title")

            if title:
                slug = generate_slug(title)
                lowercase_title = title.lower()

                # If duplicate, check which file is more recent
                if lowercase_title in registry:
                    # Get modification times (using current file's time as tie-breaker)
                    # For now, just overwrite - most recent file wins
                    pass

                registry[lowercase_title] = slug
        except Exception:
            # Skip files that can't be parsed
            pass

    # Scan existing _posts/ directory if it exists
    if posts_dir and posts_dir.exists():
        for post_file in posts_dir.glob("*.md"):
            add_to_registry(post_file)

    # Add current Ready/ batch files
    for ready_file in ready_files:
        add_to_registry(ready_file)

    return registry


def extract_frontmatter_and_content(file_path: Path) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and content from a markdown file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Check if file starts with frontmatter
    if content.startswith("---\n"):
        # Find the end of frontmatter
        end_match = re.search(r"\n---\n", content[4:])
        if end_match:
            frontmatter_text = content[4 : end_match.start() + 4]
            body = content[end_match.end() + 4 :]
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
                return frontmatter, body
            except yaml.YAMLError:
                pass

    # No valid frontmatter found
    return {}, content


def _resolve_svg_embed(
    link_text: str, is_embed: bool, svg_files_to_copy: list[dict]
) -> str | None:
    """Resolve SVG and Excalidraw embeds.

    Args:
        link_text: The text inside [[...]]
        is_embed: Whether this is an embed (![[...]]) or regular link
        svg_files_to_copy: List to append SVG file info to

    Returns:
        Markdown image reference with absolute path, or None if not an SVG embed
    """
    if not is_embed:
        return None

    # Check for SVG or Excalidraw patterns
    if link_text.endswith(".svg"):
        # Direct SVG embed: ![[file.svg]]
        base_name = link_text.replace(".svg", "")
        svg_filename = f"{base_name}.svg"

        svg_files_to_copy.append({"original": link_text, "svg_filename": svg_filename})

        return f"![{base_name}](/assets/{svg_filename})"

    elif link_text.endswith(".excalidraw"):
        # Excalidraw embed: ![[file.excalidraw]]
        # Need to check for both .svg and .excalidraw.svg at copy time
        base_name = link_text.replace(".excalidraw", "")

        svg_files_to_copy.append(
            {
                "original": link_text,
                "svg_filename": f"{base_name}.svg",  # Will try .excalidraw.svg too
                "base_name": base_name,
            }
        )

        return f"![{base_name}](/assets/{base_name}.svg)"

    return None


def _resolve_cross_post_link(
    link_text: str, is_embed: bool, registry: dict[str, str]
) -> str | None:
    """Resolve cross-post links using the post registry.

    Args:
        link_text: The text inside [[...]]
        is_embed: Whether this is an embed (![[...]]) - should be False for this resolver
        registry: Post registry mapping lowercase titles to slugs

    Returns:
        Markdown hyperlink [Title](/posts/slug/), or None if not found
    """
    if is_embed:
        return None

    # Look up in registry (case-insensitive)
    lowercase_text = link_text.lower()
    if lowercase_text in registry:
        slug = registry[lowercase_text]
        return f"[{link_text}](/posts/{slug}/)"

    return None


def _resolve_vault_link_fallback(
    link_text: str, is_embed: bool, post_title: str
) -> str:
    """Fallback resolver for vault-only links - converts to plain text with warning.

    Args:
        link_text: The text inside [[...]]
        is_embed: Whether this is an embed
        post_title: Title of the current post (for warning message)

    Returns:
        Plain text (always succeeds - this is the fallback)
    """
    # Emit warning
    logging.warning(
        f'unresolved link [[{link_text}]] in "{post_title}" -- converted to plain text'
    )

    return link_text


def _exclude_code_blocks(content: str) -> tuple[str, list[str]]:
    """Remove code blocks from content and return placeholders.

    Args:
        content: Markdown content

    Returns:
        Tuple of (content with placeholders, list of code blocks)
    """
    code_blocks = []

    # Extract fenced code blocks
    def replace_fenced(match):
        code_blocks.append(match.group(0))
        return f"<<<CODE_BLOCK_{len(code_blocks) - 1}>>>"

    content = re.sub(r"```.*?```", replace_fenced, content, flags=re.DOTALL)

    # Extract inline code spans
    def replace_inline(match):
        code_blocks.append(match.group(0))
        return f"<<<CODE_BLOCK_{len(code_blocks) - 1}>>>"

    content = re.sub(r"`[^`]+`", replace_inline, content)

    return content, code_blocks


def _restore_code_blocks(content: str, code_blocks: list[str]) -> str:
    """Restore code blocks from placeholders.

    Args:
        content: Content with placeholders
        code_blocks: List of code blocks to restore

    Returns:
        Content with code blocks restored
    """
    for i, block in enumerate(code_blocks):
        content = content.replace(f"<<<CODE_BLOCK_{i}>>>", block)

    return content


def convert_obsidian_links(
    content: str,
    registry: dict[str, str] | None = None,
    post_title: str = "Unknown",
    assets_dir: str | None = None,
) -> tuple[str, list[dict]]:
    """Convert Obsidian [[links]] using priority-ordered resolution pipeline.

    Resolution order:
    1. SVG embed resolver (for ![[file.svg]] and ![[file.excalidraw]])
    2. Cross-post link resolver (for [[Post Title]] in registry)
    3. Vault-only fallback (plain text with warning)

    Args:
        content: Markdown content to process
        registry: Optional post registry for cross-post link resolution
        post_title: Title of current post (for warning messages)
        assets_dir: Deprecated, kept for compatibility

    Returns:
        tuple: (converted_content, list_of_svg_files_to_copy)
    """
    if registry is None:
        registry = {}

    svg_files_to_copy = []

    # Exclude code blocks from processing
    content, code_blocks = _exclude_code_blocks(content)

    def resolve_link(match):
        """Process a single wikilink through the resolution pipeline."""
        is_embed = match.group(0).startswith("!")
        link_text = match.group(1)

        # Try each resolver in order
        result = _resolve_svg_embed(link_text, is_embed, svg_files_to_copy)
        if result is not None:
            return result

        result = _resolve_cross_post_link(link_text, is_embed, registry)
        if result is not None:
            return result

        # Fallback always succeeds
        return _resolve_vault_link_fallback(link_text, is_embed, post_title)

    # Process all wikilinks
    content = re.sub(r"!?\[\[([^\]]+)\]\]", resolve_link, content)

    # Restore code blocks
    content = _restore_code_blocks(content, code_blocks)

    return content, svg_files_to_copy


def copy_excalidraw_assets(
    excalidraw_files: list[dict],
    source_dir: Path,
    assets_dir: Path,
    svg_dir: Path | None = None,
) -> list[str]:
    """Copy SVG and Excalidraw files to the blog assets directory.

    Args:
        excalidraw_files: List of dicts with 'original' and 'svg_filename' keys
        source_dir: Directory containing the source markdown (to look for SVG files)
        assets_dir: Target directory for SVG files
        svg_dir: Optional dedicated SVG source directory (searched first)

    Returns:
        List of successfully copied SVG filenames

    Supports .svg, .excalidraw, and .excalidraw.svg naming patterns.
    Search order: svg_dir (if provided), source_dir, Blog/assets/
    """
    copied_files = []
    assets_dir.mkdir(parents=True, exist_ok=True)

    for file_info in excalidraw_files:
        svg_filename = file_info["svg_filename"]
        base_name = file_info.get("base_name")

        # Build list of potential filenames to look for
        # For .excalidraw files, try both .svg and .excalidraw.svg
        filenames_to_try = [svg_filename]
        if base_name and file_info.get("original", "").endswith(".excalidraw"):
            filenames_to_try.append(f"{base_name}.excalidraw.svg")

        # Build search locations in priority order
        search_dirs = []
        if svg_dir:
            search_dirs.append(svg_dir)
        search_dirs.extend(
            [
                source_dir,  # Same directory as markdown file
                source_dir.parent / "assets",  # Blog/assets/
            ]
        )

        # Try to find the file
        svg_found = False
        found_filename = None

        for search_dir in search_dirs:
            for filename in filenames_to_try:
                source_svg = search_dir / filename
                if source_svg.exists():
                    # Determine target filename - use the actual filename found
                    target_svg = assets_dir / filename
                    found_filename = filename

                    # Only copy if source and target are different files
                    if source_svg.resolve() != target_svg.resolve():
                        shutil.copy2(source_svg, target_svg)
                        print(f"  ✓ Copied SVG: {filename}")
                    else:
                        print(f"  ✓ SVG already in target location: {filename}")

                    copied_files.append(filename)
                    svg_found = True
                    break

            if svg_found:
                break

        if not svg_found:
            print(
                f"  ⚠ SVG not found for: {file_info['original']} (expected: {', '.join(filenames_to_try)})"
            )
            print(f"    Looked in: {[str(d) for d in search_dirs]}")

    return copied_files


def create_jekyll_frontmatter(
    original_frontmatter: dict[str, Any], title: str, date: datetime | None = None
) -> dict[str, Any]:
    """Create Jekyll-compatible frontmatter."""
    jekyll_frontmatter = {}

    # Set title
    jekyll_frontmatter["title"] = title

    # Set date
    if date:
        jekyll_frontmatter["date"] = date.strftime("%Y-%m-%d %H:%M:%S %z")
    elif "date created" in original_frontmatter:
        # Try to parse the existing date
        try:
            existing_date = datetime.fromisoformat(
                str(original_frontmatter["date created"])
            )
            jekyll_frontmatter["date"] = existing_date.strftime(
                "%Y-%m-%d %H:%M:%S -0400"
            )
        except (ValueError, TypeError):
            jekyll_frontmatter["date"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S -0400"
            )
    else:
        jekyll_frontmatter["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S -0400")

    # Copy over categories and tags if they exist
    if "categories" in original_frontmatter:
        jekyll_frontmatter["categories"] = original_frontmatter["categories"]

    if "tags" in original_frontmatter:
        jekyll_frontmatter["tags"] = original_frontmatter["tags"]

    return jekyll_frontmatter


def convert_post(
    ready_file: Path,
    published_dir: Path,
    blog_posts_dir: Path,
    blog_assets_dir: Path | None = None,
    svg_dir: Path | None = None,
    registry: dict[str, str] | None = None,
) -> str:
    """Convert a single post from Ready/ to Jekyll format."""
    print(f"Converting: {ready_file.name}")

    # Extract content
    frontmatter, content = extract_frontmatter_and_content(ready_file)

    # Get title from frontmatter or filename
    title = frontmatter.get("title", ready_file.stem.replace("-", " ").title())

    # Convert content and extract SVG files
    converted_content, excalidraw_files = convert_obsidian_links(
        content, registry=registry, post_title=title
    )

    # Copy SVG files if any were found
    if excalidraw_files and blog_assets_dir:
        copied_svgs = copy_excalidraw_assets(
            excalidraw_files, ready_file.parent, blog_assets_dir, svg_dir
        )
        if copied_svgs:
            print(f"  ✓ Processed {len(copied_svgs)} SVG diagram(s)")
    elif excalidraw_files:
        print(
            f"  ⚠ Found {len(excalidraw_files)} SVG diagram(s) but no assets directory specified"
        )

    # Create Jekyll frontmatter
    jekyll_frontmatter = create_jekyll_frontmatter(frontmatter, title)

    # Generate Jekyll filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = generate_slug(title)
    jekyll_filename = f"{date_str}-{slug}.md"

    # Create full Jekyll post content
    jekyll_content = "---\n"
    jekyll_content += yaml.dump(jekyll_frontmatter, default_flow_style=False)
    jekyll_content += "---\n\n"
    jekyll_content += converted_content

    # Write to Published directory
    published_file = published_dir / jekyll_filename
    with open(published_file, "w", encoding="utf-8") as f:
        f.write(jekyll_content)

    # Copy to blog repo
    blog_file = blog_posts_dir / jekyll_filename
    shutil.copy2(published_file, blog_file)

    print(f"✓ Published: {jekyll_filename}")
    return jekyll_filename


def publish_posts(
    ready_dir: Path,
    published_dir: Path,
    blog_posts_dir: Path,
    blog_assets_dir: Path | None = None,
    svg_dir: Path | None = None,
) -> list[str]:
    """Process all posts in Ready/ directory."""
    # Ensure directories exist
    published_dir.mkdir(exist_ok=True)

    if not ready_dir.exists():
        raise FileNotFoundError(f"Ready directory not found: {ready_dir}")

    if not blog_posts_dir.exists():
        raise FileNotFoundError(f"Blog posts directory not found: {blog_posts_dir}")

    # Find all markdown files in Ready/
    ready_files = list(ready_dir.glob("*.md"))

    if not ready_files:
        print("No posts found in Ready/ directory")
        return []

    print(f"Found {len(ready_files)} post(s) to publish:")

    # Build post registry for cross-post link resolution
    registry = build_post_registry(blog_posts_dir, ready_files)
    if registry:
        print(f"  ℹ Built post registry with {len(registry)} post(s)")

    published_files = []
    for ready_file in ready_files:
        try:
            jekyll_filename = convert_post(
                ready_file,
                published_dir,
                blog_posts_dir,
                blog_assets_dir,
                svg_dir,
                registry,
            )
            published_files.append(jekyll_filename)
        except Exception as e:
            print(f"✗ Error converting {ready_file.name}: {e}")

    print(f"\nSuccessfully published {len(published_files)} post(s)")

    if published_files:
        print("\nNext steps:")
        print("1. Review the converted posts in Blog/Published/")
        print("2. Check the posts in the blog repo")
        print("3. Commit changes to both repos")
        print("4. Move processed files from Ready/ to Drafts/ or delete them")

    return published_files
