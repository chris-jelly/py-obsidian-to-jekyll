#!/usr/bin/env python3
"""
Test suite for blog_publisher.core using pytest
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date
import pytest
from unittest.mock import patch, mock_open
import yaml

from blog_publisher.core import (
    extract_frontmatter_and_content,
    convert_obsidian_links,
    create_jekyll_frontmatter,
    convert_post,
    publish_posts,
    copy_excalidraw_assets,
    generate_slug,
    build_post_registry,
)


class TestGenerateSlug:
    """Test the generate_slug function."""

    def test_standard_title(self):
        """Test slug generation for a standard title."""
        assert (
            generate_slug("Part 1 - Airflow on K8s Introduction")
            == "part-1---airflow-on-k8s-introduction"
        )

    def test_special_characters_removed(self):
        """Test that special characters are removed from slug."""
        assert (
            generate_slug("Test & Post! With @ Special.Chars")
            == "test-post-with-specialchars"
        )

    def test_consecutive_spaces(self):
        """Test that consecutive spaces are collapsed to single hyphen."""
        assert generate_slug("Multiple   Spaces   Here") == "multiple-spaces-here"

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        assert generate_slug("Café and Résumé") == "caf-and-rsum"

    def test_empty_input(self):
        """Test handling of empty string."""
        assert generate_slug("") == ""

    def test_only_special_characters(self):
        """Test handling of string with only special characters."""
        assert generate_slug("!@#$%^&*()") == ""

    def test_leading_trailing_spaces(self):
        """Test that leading and trailing spaces are trimmed."""
        assert generate_slug("  Trimmed Title  ") == "trimmed-title"


class TestBuildPostRegistry:
    """Test the build_post_registry function."""

    def test_registry_from_posts_dir(self):
        """Test building registry from existing blog posts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            posts_dir = Path(tmpdir) / "_posts"
            posts_dir.mkdir()

            # Create a test post
            post_content = """---
title: My First Post
date: 2023-01-01
---

Content here.
"""
            post_file = posts_dir / "2023-01-01-my-first-post.md"
            post_file.write_text(post_content)

            registry = build_post_registry(posts_dir, [])

            assert "my first post" in registry
            assert registry["my first post"] == "my-first-post"

    def test_registry_includes_ready_batch(self):
        """Test that Ready/ batch files are included in registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ready_dir = Path(tmpdir) / "ready"
            ready_dir.mkdir()

            ready_content = """---
title: Draft Post
---

Draft content.
"""
            ready_file = ready_dir / "draft.md"
            ready_file.write_text(ready_content)

            registry = build_post_registry(Path(tmpdir) / "_posts", [ready_file])

            assert "draft post" in registry
            assert registry["draft post"] == "draft-post"

    def test_missing_title_frontmatter(self):
        """Test that files without title frontmatter are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            posts_dir = Path(tmpdir) / "_posts"
            posts_dir.mkdir()

            # Post without title
            post_content = """---
date: 2023-01-01
tags: [test]
---

Content.
"""
            post_file = posts_dir / "2023-01-01-no-title.md"
            post_file.write_text(post_content)

            registry = build_post_registry(posts_dir, [])

            assert len(registry) == 0

    def test_duplicate_titles(self):
        """Test that duplicate titles result in last one winning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            posts_dir = Path(tmpdir) / "_posts"
            posts_dir.mkdir()

            # Create two posts with same title
            post1 = posts_dir / "2023-01-01-duplicate.md"
            post1.write_text("---\ntitle: Duplicate Title\n---\nContent 1.")

            post2 = posts_dir / "2023-01-02-duplicate.md"
            post2.write_text("---\ntitle: Duplicate Title\n---\nContent 2.")

            registry = build_post_registry(posts_dir, [])

            # Should have exactly one entry
            assert len(registry) == 1
            assert "duplicate title" in registry

    def test_empty_directory(self):
        """Test handling of empty _posts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            posts_dir = Path(tmpdir) / "_posts"
            posts_dir.mkdir()

            registry = build_post_registry(posts_dir, [])

            assert registry == {}

    def test_case_insensitive_matching(self):
        """Test that registry uses lowercase keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            posts_dir = Path(tmpdir) / "_posts"
            posts_dir.mkdir()

            post_content = """---
title: My Capitalized Title
---

Content.
"""
            post_file = posts_dir / "test.md"
            post_file.write_text(post_content)

            registry = build_post_registry(posts_dir, [])

            assert "my capitalized title" in registry
            assert "My Capitalized Title" not in registry


class TestExtractFrontmatterAndContent:
    """Test the extract_frontmatter_and_content function."""

    def test_valid_frontmatter(self):
        """Test extracting valid YAML frontmatter."""
        content = """---
title: Test Post
date: 2023-01-01
tags: [test, blog]
---

This is the content of the post.
"""
        with patch("builtins.open", mock_open(read_data=content)):
            frontmatter, body = extract_frontmatter_and_content(Path("test.md"))

        expected_frontmatter = {
            "title": "Test Post",
            "date": date(2023, 1, 1),  # YAML loader converts to date object
            "tags": ["test", "blog"],
        }
        expected_body = "\nThis is the content of the post.\n"

        assert frontmatter == expected_frontmatter
        assert body == expected_body

    def test_no_frontmatter(self):
        """Test file without frontmatter."""
        content = "Just regular content without frontmatter."

        with patch("builtins.open", mock_open(read_data=content)):
            frontmatter, body = extract_frontmatter_and_content(Path("test.md"))

        assert frontmatter == {}
        assert body == content

    def test_invalid_yaml_frontmatter(self):
        """Test file with invalid YAML frontmatter."""
        content = """---
title: Test Post
invalid: [ unclosed bracket
---

Content here.
"""
        with patch("builtins.open", mock_open(read_data=content)):
            frontmatter, body = extract_frontmatter_and_content(Path("test.md"))

        assert frontmatter == {}
        assert body == content

    def test_frontmatter_without_end_marker(self):
        """Test frontmatter without closing marker."""
        content = """---
title: Test Post
tags: [test]

Content without proper frontmatter end.
"""
        with patch("builtins.open", mock_open(read_data=content)):
            frontmatter, body = extract_frontmatter_and_content(Path("test.md"))

        assert frontmatter == {}
        assert body == content


class TestConvertObsidianLinks:
    """Test the convert_obsidian_links function."""

    def test_simple_obsidian_link_unresolved(self):
        """Test converting simple unresolved Obsidian links to plain text."""
        content = "Check out [[My Other Note]] for more info."
        result, svg_files = convert_obsidian_links(content)
        expected = "Check out My Other Note for more info."
        assert result == expected
        assert svg_files == []

    def test_multiple_obsidian_links_unresolved(self):
        """Test converting multiple unresolved Obsidian links."""
        content = "See [[First Note]] and [[Second Note]] for details."
        result, svg_files = convert_obsidian_links(content)
        expected = "See First Note and Second Note for details."
        assert result == expected
        assert svg_files == []

    def test_obsidian_link_with_spaces(self):
        """Test converting Obsidian links with spaces."""
        content = "Reference [[My Note With Spaces]] here."
        result, svg_files = convert_obsidian_links(content)
        expected = "Reference My Note With Spaces here."
        assert result == expected
        assert svg_files == []

    def test_no_obsidian_links(self):
        """Test content without Obsidian links."""
        content = "Regular markdown content with no special links."
        result, svg_files = convert_obsidian_links(content)
        assert result == content
        assert svg_files == []

    def test_obsidian_link_with_special_characters(self):
        """Test converting Obsidian links with special characters."""
        content = "See [[Note-with_underscores.and.dots]] for more."
        result, svg_files = convert_obsidian_links(content)
        expected = "See Note-with_underscores.and.dots for more."
        assert result == expected
        assert svg_files == []

    def test_obsidian_link_with_registry_match(self):
        """Test cross-post link resolution with registry."""
        content = "See [[My First Post]] for background."
        registry = {"my first post": "my-first-post"}
        result, svg_files = convert_obsidian_links(content, registry=registry)
        expected = "See [My First Post](/posts/my-first-post/) for background."
        assert result == expected
        assert svg_files == []


class TestExcalidrawConversion:
    """Test SVG and Excalidraw embed functionality."""

    def test_excalidraw_embed_conversion(self):
        """Test converting Excalidraw embeds to image links with absolute paths."""
        content = "Check out this diagram: ![[My Diagram.excalidraw]]"
        result, svg_files = convert_obsidian_links(content)

        expected = "Check out this diagram: ![My Diagram](/assets/My Diagram.svg)"
        assert result == expected
        assert len(svg_files) == 1
        assert svg_files[0]["original"] == "My Diagram.excalidraw"
        assert svg_files[0]["svg_filename"] == "My Diagram.svg"

    def test_svg_embed_conversion(self):
        """Test converting direct SVG embeds."""
        content = "See the diagram: ![[diagram.svg]]"
        result, svg_files = convert_obsidian_links(content)

        expected = "See the diagram: ![diagram](/assets/diagram.svg)"
        assert result == expected
        assert len(svg_files) == 1
        assert svg_files[0]["original"] == "diagram.svg"
        assert svg_files[0]["svg_filename"] == "diagram.svg"

    def test_mixed_links_and_svg(self):
        """Test content with both regular links and SVG embeds."""
        content = "Read [[My Notes]] and see ![[System Design.excalidraw]] for details."
        result, svg_files = convert_obsidian_links(content)

        expected = "Read My Notes and see ![System Design](/assets/System Design.svg) for details."
        assert result == expected
        assert len(svg_files) == 1
        assert svg_files[0]["original"] == "System Design.excalidraw"
        assert svg_files[0]["svg_filename"] == "System Design.svg"

    def test_multiple_svg_files(self):
        """Test content with multiple SVG embeds."""
        content = "See ![[Diagram1.excalidraw]] and ![[diagram2.svg]] for reference."
        result, svg_files = convert_obsidian_links(content)

        expected = "See ![Diagram1](/assets/Diagram1.svg) and ![diagram2](/assets/diagram2.svg) for reference."
        assert result == expected
        assert len(svg_files) == 2

        assert svg_files[0]["original"] == "Diagram1.excalidraw"
        assert svg_files[0]["svg_filename"] == "Diagram1.svg"

        assert svg_files[1]["original"] == "diagram2.svg"
        assert svg_files[1]["svg_filename"] == "diagram2.svg"


class TestCopyExcalidrawAssets:
    """Test the copy_excalidraw_assets function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.test_dir) / "source"
        self.assets_dir = Path(self.test_dir) / "assets"
        self.source_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_copy_svg_from_same_directory(self):
        """Test copying SVG file from same directory as markdown."""
        # Create a test SVG file
        test_svg = self.source_dir / "test-diagram.svg"
        test_svg.write_text("<svg>test</svg>")

        excalidraw_files = [
            {"original": "test-diagram.excalidraw", "svg_filename": "test-diagram.svg"}
        ]

        copied = copy_excalidraw_assets(
            excalidraw_files, self.source_dir, self.assets_dir
        )

        assert len(copied) == 1
        assert copied[0] == "test-diagram.svg"
        assert (self.assets_dir / "test-diagram.svg").exists()
        assert (self.assets_dir / "test-diagram.svg").read_text() == "<svg>test</svg>"

    def test_copy_svg_from_assets_subdirectory(self):
        """Test copying SVG file from Blog/assets/ directory."""
        # Create assets subdirectory and SVG file
        blog_assets_dir = self.source_dir.parent / "assets"
        blog_assets_dir.mkdir()
        test_svg = blog_assets_dir / "diagram.svg"
        test_svg.write_text("<svg>content</svg>")

        excalidraw_files = [
            {"original": "diagram.excalidraw", "svg_filename": "diagram.svg"}
        ]

        copied = copy_excalidraw_assets(
            excalidraw_files, self.source_dir, self.assets_dir
        )

        assert len(copied) == 1
        assert (self.assets_dir / "diagram.svg").exists()

    def test_svg_file_not_found(self):
        """Test behavior when SVG file cannot be found."""
        excalidraw_files = [
            {"original": "missing.excalidraw", "svg_filename": "missing.svg"}
        ]

        copied = copy_excalidraw_assets(
            excalidraw_files, self.source_dir, self.assets_dir
        )

        assert len(copied) == 0
        assert not (self.assets_dir / "missing.svg").exists()


class TestCreateJekyllFrontmatter:
    """Test the create_jekyll_frontmatter function."""

    def test_basic_frontmatter_creation(self):
        """Test creating basic Jekyll frontmatter."""
        original = {}
        title = "Test Post"
        date = datetime(2023, 1, 15, 10, 30, 0)

        result = create_jekyll_frontmatter(original, title, date)

        assert result["title"] == "Test Post"
        # Note: %z format depends on system timezone, so we check for the date/time portion
        assert result["date"].startswith("2023-01-15 10:30:00")

    def test_frontmatter_with_categories_and_tags(self):
        """Test preserving categories and tags."""
        original = {"categories": ["tech", "blog"], "tags": ["python", "testing"]}
        title = "Test Post"

        result = create_jekyll_frontmatter(original, title)

        assert result["title"] == "Test Post"
        assert result["categories"] == ["tech", "blog"]
        assert result["tags"] == ["python", "testing"]
        assert "date" in result

    def test_frontmatter_without_date(self):
        """Test frontmatter creation without provided date."""
        original = {}
        title = "Test Post"

        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = (
                "2023-01-01 12:00:00 -0400"
            )
            result = create_jekyll_frontmatter(original, title)

        assert result["title"] == "Test Post"
        assert result["date"] == "2023-01-01 12:00:00 -0400"

    def test_frontmatter_with_date_created(self):
        """Test behavior when 'date created' field exists (currently uses current time)."""
        original = {"date created": "2023-01-01"}
        title = "Test Post"

        result = create_jekyll_frontmatter(original, title)

        assert result["title"] == "Test Post"
        # Should parse the 'date created' field and use it
        assert result["date"].endswith(" -0400")  # Should have timezone
        # Verify it uses the date from frontmatter
        result_date = result["date"].split()[0]
        assert result_date == "2023-01-01"


class TestSlugGeneration:
    """Test slug generation behavior in convert_post function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.ready_dir = Path(self.test_dir) / "Ready"
        self.published_dir = Path(self.test_dir) / "Published"
        self.blog_posts_dir = Path(self.test_dir) / "blog_posts"

        self.ready_dir.mkdir()
        self.published_dir.mkdir()
        self.blog_posts_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_slug_with_special_characters(self):
        """Test slug generation removes special characters."""
        test_file = self.ready_dir / "test.md"
        with open(test_file, "w") as f:
            f.write("""---
title: "My Post: A Guide to Python & Django!"
---

Test content.
""")

        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            result = convert_post(test_file, self.published_dir, self.blog_posts_dir)

        # Should remove special characters and convert to lowercase
        assert "my-post-a-guide-to-python-django" in result
        assert ":" not in result
        assert "&" not in result
        assert "!" not in result

    def test_slug_with_multiple_spaces(self):
        """Test slug generation handles multiple consecutive spaces."""
        test_file = self.ready_dir / "test.md"
        with open(test_file, "w") as f:
            f.write("""---
title: "My    Post   With     Spaces"
---

Test content.
""")

        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            result = convert_post(test_file, self.published_dir, self.blog_posts_dir)

        # Multiple spaces should be converted to single hyphens
        assert "my-post-with-spaces" in result
        assert "--" not in result  # No double hyphens

    def test_slug_with_unicode_characters(self):
        """Test slug generation with unicode characters."""
        test_file = self.ready_dir / "test.md"
        with open(test_file, "w") as f:
            f.write("""---
title: "Café Résumé naïve"
---

Test content.
""")

        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            result = convert_post(test_file, self.published_dir, self.blog_posts_dir)

        # Unicode characters should be removed, leaving basic words
        assert (
            "caf-rsum-nave" in result.lower() or "cafe-resume-naive" in result.lower()
        )

    def test_slug_with_numbers_and_hyphens(self):
        """Test slug generation preserves numbers and existing hyphens."""
        test_file = self.ready_dir / "test.md"
        with open(test_file, "w") as f:
            f.write("""---
title: "Python 3.9 - Best Practices 2023"
---

Test content.
""")

        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            result = convert_post(test_file, self.published_dir, self.blog_posts_dir)

        # Numbers should be preserved, periods removed, may have multiple hyphens
        assert "python-39" in result  # Period in 3.9 gets removed
        assert "best-practices-2023" in result
        assert "3" in result
        assert "9" in result


class TestConvertPost:
    """Test the convert_post function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.ready_dir = Path(self.test_dir) / "Ready"
        self.published_dir = Path(self.test_dir) / "Published"
        self.blog_posts_dir = Path(self.test_dir) / "blog_posts"

        self.ready_dir.mkdir()
        self.published_dir.mkdir()
        self.blog_posts_dir.mkdir()

        # Create a test file
        self.test_file = self.ready_dir / "test-post.md"
        with open(self.test_file, "w") as f:
            f.write("""---
title: Test Post Title
categories: [tech]
tags: [python, testing]
---

This is a test post with [[Internal Link]] and regular content.
""")

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_convert_post_success(self):
        """Test successful post conversion."""
        with patch("blog_publisher.core.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                "%Y-%m-%d": "2023-01-15",
                "%Y-%m-%d %H:%M:%S -0400": "2023-01-15 12:00:00 -0400",
            }[fmt]

            result = convert_post(
                self.test_file, self.published_dir, self.blog_posts_dir
            )

        assert isinstance(result, str)
        assert result.startswith("2023-01-15-")
        assert result.endswith(".md")

        # Check files were created
        assert (self.published_dir / result).exists()
        assert (self.blog_posts_dir / result).exists()


class TestPublishPosts:
    """Test the publish_posts function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.ready_dir = Path(self.test_dir) / "Ready"
        self.published_dir = Path(self.test_dir) / "Published"
        self.blog_posts_dir = Path(self.test_dir) / "blog_posts"

        self.ready_dir.mkdir()
        self.blog_posts_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_publish_posts_no_ready_files(self):
        """Test publish_posts with no files to process."""
        result = publish_posts(self.ready_dir, self.published_dir, self.blog_posts_dir)
        assert result == []

    def test_publish_posts_ready_dir_not_exists(self):
        """Test publish_posts when Ready directory doesn't exist."""
        non_existent_dir = Path(self.test_dir) / "NonExistent"

        with pytest.raises(FileNotFoundError, match="Ready directory not found"):
            publish_posts(non_existent_dir, self.published_dir, self.blog_posts_dir)

    def test_publish_posts_blog_dir_not_exists(self):
        """Test publish_posts when blog posts directory doesn't exist."""
        non_existent_dir = Path(self.test_dir) / "NonExistent"

        with pytest.raises(FileNotFoundError, match="Blog posts directory not found"):
            publish_posts(self.ready_dir, self.published_dir, non_existent_dir)


# Pytest fixtures for integration testing
@pytest.fixture
def temp_blog_env(tmp_path):
    """Create a temporary blog environment for testing."""
    ready_dir = tmp_path / "Ready"
    published_dir = tmp_path / "Published"
    blog_posts_dir = tmp_path / "blog_posts"

    ready_dir.mkdir()
    published_dir.mkdir()
    blog_posts_dir.mkdir()

    return {
        "ready_dir": ready_dir,
        "published_dir": published_dir,
        "blog_posts_dir": blog_posts_dir,
        "temp_dir": tmp_path,
    }


@pytest.fixture
def sample_post_file(temp_blog_env):
    """Create a sample post file for testing."""
    post_content = """---
title: Integration Test Post
categories: [tech, testing]
tags: [pytest, python]
---

# Integration Test

This is a sample post for integration testing.

It contains [[Internal Links]] that should be converted.
"""
    post_file = temp_blog_env["ready_dir"] / "integration-test.md"
    post_file.write_text(post_content)
    return post_file


class TestIntegration:
    """Integration tests using real file operations."""

    def test_end_to_end_conversion(self, temp_blog_env, sample_post_file):
        """Test complete post conversion process."""
        result = convert_post(
            sample_post_file,
            temp_blog_env["published_dir"],
            temp_blog_env["blog_posts_dir"],
        )

        # Check that files were created
        published_files = list(temp_blog_env["published_dir"].glob("*.md"))
        blog_files = list(temp_blog_env["blog_posts_dir"].glob("*.md"))

        assert len(published_files) == 1
        assert len(blog_files) == 1
        assert published_files[0].name == result

        # Check content transformation
        published_content = published_files[0].read_text()
        assert "title: Integration Test Post" in published_content
        # With new behavior, unresolved links become plain text (not backticks)
        assert "Internal Links" in published_content
        assert "[[Internal Links]]" not in published_content


class TestCrossPostLinking:
    """Test cross-post link resolution functionality."""

    def test_exact_title_match(self):
        """Test cross-post linking with exact title match."""
        content = "See [[Part 1 - Airflow on K8s Introduction]] for more."
        registry = {
            "part 1 - airflow on k8s introduction": "part-1---airflow-on-k8s-introduction"
        }
        result, _ = convert_obsidian_links(content, registry=registry)

        expected = "See [Part 1 - Airflow on K8s Introduction](/posts/part-1---airflow-on-k8s-introduction/) for more."
        assert result == expected

    def test_case_insensitive_matching(self):
        """Test that cross-post matching is case-insensitive."""
        content = "Read [[my post title]] for details."
        registry = {"my post title": "my-post-title"}
        result, _ = convert_obsidian_links(content, registry=registry)

        expected = "Read [my post title](/posts/my-post-title/) for details."
        assert result == expected

    def test_slug_generation_consistency(self):
        """Test that slug generation is consistent between registry and links."""
        # Build a registry entry
        registry = {"test post": generate_slug("Test Post")}

        content = "See [[Test Post]] for info."
        result, _ = convert_obsidian_links(content, registry=registry)

        expected = "See [Test Post](/posts/test-post/) for info."
        assert result == expected

    def test_no_match_in_registry(self):
        """Test that unmatched links fall back to plain text."""
        content = "See [[Unknown Post]] for details."
        registry = {"known post": "known-post"}
        result, _ = convert_obsidian_links(content, registry=registry)

        expected = "See Unknown Post for details."
        assert result == expected


class TestVaultLinkFallback:
    """Test vault-only link fallback behavior."""

    def test_plain_text_output(self):
        """Test that unresolved links become plain text."""
        content = "Check [[Concept Diagram]] for understanding."
        result, _ = convert_obsidian_links(content)

        expected = "Check Concept Diagram for understanding."
        assert result == expected

    def test_special_characters_preserved(self):
        """Test that special characters are preserved in plain text."""
        content = "See [[My Note (Draft)]] for more."
        result, _ = convert_obsidian_links(content)

        expected = "See My Note (Draft) for more."
        assert result == expected

    def test_multiple_unresolved_links(self):
        """Test multiple unresolved links in one post."""
        content = "Read [[Note A]] and [[Note B]] for context."
        result, _ = convert_obsidian_links(content)

        expected = "Read Note A and Note B for context."
        assert result == expected

    def test_warning_emission(self, caplog):
        """Test that warnings are emitted for unresolved links."""
        import logging

        caplog.set_level(logging.WARNING)

        content = "See [[Kubernetes]] for info."
        convert_obsidian_links(content, post_title="My Blog Post")

        assert "unresolved link [[Kubernetes]]" in caplog.text
        assert 'in "My Blog Post"' in caplog.text
        assert "converted to plain text" in caplog.text

    def test_no_warning_for_resolved_links(self, caplog):
        """Test that no warnings are emitted for resolved links."""
        import logging

        caplog.set_level(logging.WARNING)

        content = "See [[Known Post]] for details."
        registry = {"known post": "known-post"}
        convert_obsidian_links(content, registry=registry, post_title="Test Post")

        # Should not have any warnings about unresolved links
        assert "unresolved link" not in caplog.text


class TestLinkResolutionPipeline:
    """Test the priority-ordered link resolution pipeline."""

    def test_svg_takes_priority_over_cross_post(self):
        """Test that SVG embed resolver takes priority."""
        content = "See ![[diagram.svg]] for the architecture."
        # Even if there's a post titled "diagram.svg", the SVG resolver wins
        registry = {"diagram.svg": "diagram-svg"}
        result, svg_files = convert_obsidian_links(content, registry=registry)

        expected = "See ![diagram](/assets/diagram.svg) for the architecture."
        assert result == expected
        assert len(svg_files) == 1

    def test_cross_post_takes_priority_over_fallback(self):
        """Test that cross-post resolver takes priority over fallback."""
        content = "Read [[My Post Title]] for background."
        registry = {"my post title": "my-post-title"}
        result, _ = convert_obsidian_links(content, registry=registry)

        # Should be a hyperlink, not plain text
        expected = "Read [My Post Title](/posts/my-post-title/) for background."
        assert result == expected

    def test_fallback_when_no_match(self):
        """Test that fallback handles unmatched links."""
        content = "See [[Random Note]] for info."
        registry = {"other post": "other-post"}
        result, _ = convert_obsidian_links(content, registry=registry)

        expected = "See Random Note for info."
        assert result == expected

    def test_embed_vs_link_routing(self):
        """Test that embed syntax routes to SVG, link syntax to cross-post."""
        content = "See ![[file.svg]] and [[Post Title]] for details."
        registry = {"post title": "post-title"}
        result, svg_files = convert_obsidian_links(content, registry=registry)

        expected = "See ![file](/assets/file.svg) and [Post Title](/posts/post-title/) for details."
        assert result == expected
        assert len(svg_files) == 1

    def test_code_block_exclusion_fenced(self):
        """Test that wikilinks in fenced code blocks are not processed."""
        content = """Regular [[link]] here.

```python
# This [[link]] should not be converted
x = "[[another link]]"
```

Another [[link]] here."""

        registry = {"link": "link"}
        result, _ = convert_obsidian_links(content, registry=registry)

        # Links outside code blocks should be resolved
        assert "[link](/posts/link/)" in result
        # Links inside code blocks should remain unchanged
        assert "# This [[link]] should not be converted" in result

    def test_code_block_exclusion_inline(self):
        """Test that wikilinks in inline code are not processed."""
        content = "Regular [[link]] and inline `[[code link]]` here."
        registry = {"link": "link"}
        result, _ = convert_obsidian_links(content, registry=registry)

        # Regular link should be resolved
        assert "[link](/posts/link/)" in result
        # Inline code link should remain unchanged
        assert "`[[code link]]`" in result


class TestSVGHandling:
    """Test SVG file handling enhancements."""

    def test_svg_search_order(self):
        """Test that SVG files are searched in the correct priority order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directories
            svg_dir = Path(tmpdir) / "svg"
            source_dir = Path(tmpdir) / "source"
            assets_dir = Path(tmpdir) / "assets"

            svg_dir.mkdir()
            source_dir.mkdir()
            assets_dir.mkdir()

            # Create SVG file in svg_dir (highest priority)
            (svg_dir / "test.svg").write_text("<svg>from svg_dir</svg>")
            (source_dir / "test.svg").write_text("<svg>from source_dir</svg>")

            svg_files = [{"original": "test.svg", "svg_filename": "test.svg"}]

            result = copy_excalidraw_assets(svg_files, source_dir, assets_dir, svg_dir)

            assert len(result) == 1
            # Should have copied from svg_dir (highest priority)
            assert (assets_dir / "test.svg").read_text() == "<svg>from svg_dir</svg>"

    def test_excalidraw_svg_pattern(self):
        """Test support for .excalidraw.svg naming pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            assets_dir = Path(tmpdir) / "assets"

            source_dir.mkdir()
            assets_dir.mkdir()

            # Create a file with .excalidraw.svg extension
            (source_dir / "diagram.excalidraw.svg").write_text(
                "<svg>excalidraw diagram</svg>"
            )

            # Simulating ![[diagram.excalidraw]] which should find diagram.excalidraw.svg
            svg_files = [
                {
                    "original": "diagram.excalidraw",
                    "svg_filename": "diagram.svg",
                    "base_name": "diagram",
                }
            ]

            result = copy_excalidraw_assets(svg_files, source_dir, assets_dir)

            assert len(result) == 1
            # Should have found and copied the .excalidraw.svg file
            assert (assets_dir / "diagram.excalidraw.svg").exists()

    def test_missing_file_warning(self, capsys):
        """Test that warnings are emitted for missing SVG files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            assets_dir = Path(tmpdir) / "assets"

            source_dir.mkdir()
            assets_dir.mkdir()

            svg_files = [{"original": "missing.svg", "svg_filename": "missing.svg"}]

            result = copy_excalidraw_assets(svg_files, source_dir, assets_dir)

            assert len(result) == 0
            captured = capsys.readouterr()
            assert "SVG not found" in captured.out
            assert "missing.svg" in captured.out


class TestMultiPostIntegration:
    """Integration test for multi-post batch with cross-references."""

    def test_multi_post_cross_references_and_svgs(self):
        """Test publishing multiple posts with cross-references and SVG embeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ready_dir = Path(tmpdir) / "Ready"
            published_dir = Path(tmpdir) / "Published"
            blog_posts_dir = Path(tmpdir) / "_posts"
            blog_assets_dir = Path(tmpdir) / "assets"
            svg_dir = Path(tmpdir) / "svg"

            ready_dir.mkdir()
            blog_posts_dir.mkdir()
            blog_assets_dir.mkdir()
            svg_dir.mkdir()

            # Create SVG file
            (svg_dir / "architecture.svg").write_text("<svg>test</svg>")

            # Create first post
            post1_content = """---
title: Introduction to the System
---

This is the introduction. See ![[architecture.svg]] for an overview."""
            (ready_dir / "intro.md").write_text(post1_content)

            # Create second post that references the first
            post2_content = """---
title: Deep Dive
---

Building on [[Introduction to the System]], let's explore more details."""
            (ready_dir / "deep-dive.md").write_text(post2_content)

            # Publish the posts
            with patch("blog_publisher.core.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                    "%Y-%m-%d": "2024-01-15",
                    "%Y-%m-%d %H:%M:%S -0400": "2024-01-15 12:00:00 -0400",
                }[fmt]

                result = publish_posts(
                    ready_dir, published_dir, blog_posts_dir, blog_assets_dir, svg_dir
                )

            assert len(result) == 2

            # Check that SVG was copied
            assert (blog_assets_dir / "architecture.svg").exists()

            # Read the published posts
            deep_dive_file = published_dir / "2024-01-15-deep-dive.md"
            assert deep_dive_file.exists()

            deep_dive_content = deep_dive_file.read_text()

            # Verify cross-post link was resolved
            assert (
                "[Introduction to the System](/posts/introduction-to-the-system/)"
                in deep_dive_content
            )

            # Read the intro post to verify SVG embed
            intro_file = published_dir / "2024-01-15-introduction-to-the-system.md"
            intro_content = intro_file.read_text()

            # Verify SVG embed with absolute path
            assert "![architecture](/assets/architecture.svg)" in intro_content
