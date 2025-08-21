#!/usr/bin/env python3
"""
Test suite for blog_publisher.cli using pytest
"""
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import pytest
from click.testing import CliRunner

from blog_publisher.cli import main, detect_default_paths


class TestCLI:
    """Test the command-line interface."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.ready_dir = Path(self.test_dir) / "Ready"
        self.published_dir = Path(self.test_dir) / "Published"
        self.blog_posts_dir = Path(self.test_dir) / "blog_posts"
        
        self.ready_dir.mkdir()
        self.published_dir.mkdir()
        self.blog_posts_dir.mkdir()
        
        self.runner = CliRunner()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_cli_with_all_args(self):
        """Test CLI with all required arguments."""
        # Create a test post
        test_post = self.ready_dir / "test.md"
        test_post.write_text("""---
title: CLI Test Post
---

Test content for CLI.
""")
        
        result = self.runner.invoke(main, [
            '--ready-dir', str(self.ready_dir),
            '--published-dir', str(self.published_dir),
            '--blog-dir', str(self.blog_posts_dir),
        ])
        
        assert result.exit_code == 0
        assert "Successfully published 1 post(s)" in result.output
    
    def test_cli_no_posts(self):
        """Test CLI when no posts are found."""
        result = self.runner.invoke(main, [
            '--ready-dir', str(self.ready_dir),
            '--published-dir', str(self.published_dir), 
            '--blog-dir', str(self.blog_posts_dir),
        ])
        
        assert result.exit_code == 0
        assert "No posts found to publish" in result.output
    
    def test_cli_missing_ready_dir(self):
        """Test CLI with missing ready directory."""
        result = self.runner.invoke(main, [
            '--published-dir', str(self.published_dir),
            '--blog-dir', str(self.blog_posts_dir),
        ])
        
        assert result.exit_code == 1
        assert "Could not find Ready directory" in result.output
    
    def test_cli_invalid_ready_dir(self):
        """Test CLI with non-existent ready directory."""
        result = self.runner.invoke(main, [
            '--ready-dir', '/non/existent/path',
            '--published-dir', str(self.published_dir),
            '--blog-dir', str(self.blog_posts_dir),
        ])
        
        assert result.exit_code == 2  # Click validation error


class TestDetectDefaultPaths:
    """Test the detect_default_paths function."""
    
    def test_detect_paths_in_jelly_brain(self):
        """Test path detection when in jelly-brain repo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create jelly-brain structure
            blog_dir = Path(temp_dir) / "Blog"
            blog_dir.mkdir()
            (blog_dir / "Ready").mkdir()
            (blog_dir / "Published").mkdir()
            
            with patch('blog_publisher.cli.Path.cwd', return_value=Path(temp_dir)):
                paths = detect_default_paths()
            
            assert paths['ready_dir'] == Path(temp_dir) / "Blog" / "Ready"
            assert paths['published_dir'] == Path(temp_dir) / "Blog" / "Published"
    
    def test_detect_paths_no_structure(self):
        """Test path detection when no expected structure exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('blog_publisher.cli.Path.cwd', return_value=Path(temp_dir)), \
                 patch('blog_publisher.cli.Path.home', return_value=Path(temp_dir)):
                paths = detect_default_paths()
            
            assert paths['ready_dir'] is None
            assert paths['published_dir'] is None
            assert paths['blog_dir'] is None