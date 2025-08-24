"""
Core functionality for converting Obsidian notes to Jekyll blog posts.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml


def extract_frontmatter_and_content(file_path: Path) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and content from a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
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


def convert_obsidian_links(
    content: str, assets_dir: Optional[str] = None
) -> tuple[str, list[str]]:
    """Convert Obsidian [[links]] to markdown links or remove internal ones.

    Returns:
        tuple: (converted_content, list_of_excalidraw_files)
    """
    excalidraw_files = []

    def convert_link(match):
        link_text = match.group(1)

        # Check for Excalidraw files
        if link_text.endswith(".excalidraw"):
            # Extract filename without extension for SVG
            base_name = link_text.replace(".excalidraw", "")
            svg_filename = f"{base_name}.svg"

            # Add to list of files to copy
            excalidraw_files.append(
                {"original": link_text, "svg_filename": svg_filename}
            )

            # Convert to standard markdown image
            if assets_dir:
                return f"![{base_name}]({assets_dir}/{svg_filename})"
            else:
                return f"![{base_name}](assets/{svg_filename})"
        else:
            # Regular Obsidian link - convert to code block as before
            return f"`{link_text}`"

    # Handle both embed syntax ![[file]] and link syntax [[file]]
    content = re.sub(r"!?\[\[([^\]]+)\]\]", convert_link, content)

    return content, excalidraw_files


def copy_excalidraw_assets(
    excalidraw_files: list[dict], source_dir: Path, assets_dir: Path
) -> list[str]:
    """Copy Excalidraw SVG files to the blog assets directory.

    Args:
        excalidraw_files: List of dicts with 'original' and 'svg_filename' keys
        source_dir: Directory containing the source markdown (to look for SVG files)
        assets_dir: Target directory for SVG files

    Returns:
        List of successfully copied SVG filenames
    """
    copied_files = []
    assets_dir.mkdir(parents=True, exist_ok=True)

    for file_info in excalidraw_files:
        svg_filename = file_info["svg_filename"]

        # Look for SVG file in various locations
        potential_sources = [
            source_dir / svg_filename,  # Same directory as markdown file
            source_dir.parent / "assets" / svg_filename,  # Blog/assets/
            source_dir.parent / svg_filename,  # Blog/ directory
        ]

        svg_found = False
        for source_svg in potential_sources:
            if source_svg.exists():
                target_svg = assets_dir / svg_filename
                # Only copy if source and target are different files
                if source_svg.resolve() != target_svg.resolve():
                    shutil.copy2(source_svg, target_svg)
                    print(f"  ✓ Copied SVG: {svg_filename}")
                else:
                    print(f"  ✓ SVG already in target location: {svg_filename}")
                copied_files.append(svg_filename)
                svg_found = True
                break

        if not svg_found:
            print(
                f"  ⚠ SVG not found for: {file_info['original']} (expected: {svg_filename})"
            )
            print(f"    Looked in: {[str(p) for p in potential_sources]}")

    return copied_files


def create_jekyll_frontmatter(
    original_frontmatter: dict[str, Any], title: str, date: Optional[datetime] = None
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
    blog_assets_dir: Optional[Path] = None,
) -> str:
    """Convert a single post from Ready/ to Jekyll format."""
    print(f"Converting: {ready_file.name}")

    # Extract content
    frontmatter, content = extract_frontmatter_and_content(ready_file)

    # Get title from frontmatter or filename
    title = frontmatter.get("title", ready_file.stem.replace("-", " ").title())

    # Convert content and extract Excalidraw files
    assets_path = "assets" if not blog_assets_dir else f"assets"
    converted_content, excalidraw_files = convert_obsidian_links(content, assets_path)

    # Copy Excalidraw SVG files if any were found
    if excalidraw_files and blog_assets_dir:
        copied_svgs = copy_excalidraw_assets(
            excalidraw_files, ready_file.parent, blog_assets_dir
        )
        if copied_svgs:
            print(f"  ✓ Processed {len(copied_svgs)} Excalidraw diagram(s)")
    elif excalidraw_files:
        print(
            f"  ⚠ Found {len(excalidraw_files)} Excalidraw diagram(s) but no assets directory specified"
        )

    # Create Jekyll frontmatter
    jekyll_frontmatter = create_jekyll_frontmatter(frontmatter, title)

    # Generate Jekyll filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
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
    blog_assets_dir: Optional[Path] = None,
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

    published_files = []
    for ready_file in ready_files:
        try:
            jekyll_filename = convert_post(
                ready_file, published_dir, blog_posts_dir, blog_assets_dir
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
