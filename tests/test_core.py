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
)


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
            "tags": ["test", "blog"]
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
    
    def test_simple_obsidian_link(self):
        """Test converting simple Obsidian links."""
        content = "Check out [[My Other Note]] for more info."
        result = convert_obsidian_links(content)
        expected = "Check out `My Other Note` for more info."
        assert result == expected
    
    def test_multiple_obsidian_links(self):
        """Test converting multiple Obsidian links."""
        content = "See [[First Note]] and [[Second Note]] for details."
        result = convert_obsidian_links(content)
        expected = "See `First Note` and `Second Note` for details."
        assert result == expected
    
    def test_obsidian_link_with_spaces(self):
        """Test converting Obsidian links with spaces."""
        content = "Reference [[My Note With Spaces]] here."
        result = convert_obsidian_links(content)
        expected = "Reference `My Note With Spaces` here."
        assert result == expected
    
    def test_no_obsidian_links(self):
        """Test content without Obsidian links."""
        content = "Regular markdown content with no special links."
        result = convert_obsidian_links(content)
        assert result == content
    
    def test_obsidian_link_with_special_characters(self):
        """Test converting Obsidian links with special characters."""
        content = "See [[Note-with_underscores.and.dots]] for more."
        result = convert_obsidian_links(content)
        expected = "See `Note-with_underscores.and.dots` for more."
        assert result == expected


class TestCreateJekyllFrontmatter:
    """Test the create_jekyll_frontmatter function."""
    
    def test_basic_frontmatter_creation(self):
        """Test creating basic Jekyll frontmatter."""
        original = {}
        title = "Test Post"
        date = datetime(2023, 1, 15, 10, 30, 0)
        
        result = create_jekyll_frontmatter(original, title, date)
        
        assert result['title'] == "Test Post"
        assert result['date'] == "2023-01-15 10:30:00 "
    
    def test_frontmatter_with_categories_and_tags(self):
        """Test preserving categories and tags."""
        original = {
            'categories': ['tech', 'blog'],
            'tags': ['python', 'testing']
        }
        title = "Test Post"
        
        result = create_jekyll_frontmatter(original, title)
        
        assert result['title'] == "Test Post"
        assert result['categories'] == ['tech', 'blog']
        assert result['tags'] == ['python', 'testing']
        assert 'date' in result
    
    def test_frontmatter_without_date(self):
        """Test frontmatter creation without provided date."""
        original = {}
        title = "Test Post"
        
        with patch('blog_publisher.core.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-01 12:00:00 -0400"
            result = create_jekyll_frontmatter(original, title)
        
        assert result['title'] == "Test Post"
        assert result['date'] == "2023-01-01 12:00:00 -0400"
    
    def test_frontmatter_with_date_created(self):
        """Test using existing 'date created' field."""
        original = {'date created': '2023-01-01'}
        title = "Test Post"
        
        with patch('blog_publisher.core.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-01 12:00:00 -0400"
            result = create_jekyll_frontmatter(original, title)
        
        assert result['title'] == "Test Post"
        assert result['date'] == "2023-01-01 12:00:00 -0400"


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
        with open(self.test_file, 'w') as f:
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
        with patch('blog_publisher.core.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-15"
            mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                '%Y-%m-%d': '2023-01-15',
                '%Y-%m-%d %H:%M:%S -0400': '2023-01-15 12:00:00 -0400'
            }[fmt]
            
            result = convert_post(self.test_file, self.published_dir, self.blog_posts_dir)
        
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
        'ready_dir': ready_dir,
        'published_dir': published_dir,
        'blog_posts_dir': blog_posts_dir,
        'temp_dir': tmp_path
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
    post_file = temp_blog_env['ready_dir'] / "integration-test.md"
    post_file.write_text(post_content)
    return post_file


class TestIntegration:
    """Integration tests using real file operations."""
    
    def test_end_to_end_conversion(self, temp_blog_env, sample_post_file):
        """Test complete post conversion process."""
        result = convert_post(
            sample_post_file,
            temp_blog_env['published_dir'],
            temp_blog_env['blog_posts_dir']
        )
        
        # Check that files were created
        published_files = list(temp_blog_env['published_dir'].glob("*.md"))
        blog_files = list(temp_blog_env['blog_posts_dir'].glob("*.md"))
        
        assert len(published_files) == 1
        assert len(blog_files) == 1
        assert published_files[0].name == result
        
        # Check content transformation
        published_content = published_files[0].read_text()
        assert "title: Integration Test Post" in published_content
        assert "`Internal Links`" in published_content
        assert "[[Internal Links]]" not in published_content