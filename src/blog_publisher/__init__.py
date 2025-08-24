"""
Blog Publisher: Convert Obsidian notes to Jekyll blog posts.
"""

__version__ = "0.1.0"
__author__ = "Chris Jelly"
__email__ = "chris@example.com"

from .core import (
    convert_obsidian_links,
    create_jekyll_frontmatter,
    extract_frontmatter_and_content,
    convert_post,
    publish_posts,
)

__all__ = [
    "convert_obsidian_links",
    "create_jekyll_frontmatter",
    "extract_frontmatter_and_content",
    "convert_post",
    "publish_posts",
]
