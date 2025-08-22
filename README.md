# py-obsidian-to-jekyll

Convert Obsidian notes to Jekyll blog posts with automatic frontmatter transformation and link conversion.

## Features

- ✅ Extract YAML frontmatter from Obsidian notes
- ✅ Convert `[[Obsidian links]]` to code blocks
- ✅ Generate Jekyll-compatible frontmatter with dates
- ✅ Preserve categories and tags
- ✅ Auto-generate Jekyll post filenames with dates
- ✅ Copy posts to both local and blog repository locations
- ✅ Command-line interface with smart path detection

## Installation

### As Development Dependency

```bash
# Install in development mode
uv add --dev --editable path/to/py-obsidian-to-jekyll

# Or install from git
uv add --dev git+https://github.com/chris-jelly/py-obsidian-to-jekyll.git
```

### For Local Development

```bash
cd py-obsidian-to-jekyll
uv sync
uv run blog-publish --help
```

## Usage

### Command Line

```bash
# Auto-detect paths (when run from jelly-brain repo)
blog-publish

# Specify custom paths
blog-publish \
  --ready-dir /path/to/Blog/Ready \
  --published-dir /path/to/Blog/Published \
  --blog-dir /path/to/blog-repo/_posts
```

### Python API

```python
from pathlib import Path
from blog_publisher import publish_posts

# Publish all posts in Ready/ directory
published_files = publish_posts(
    ready_dir=Path("Blog/Ready"),
    published_dir=Path("Blog/Published"), 
    blog_posts_dir=Path("../chris-jelly.github.io/_posts")
)

print(f"Published {len(published_files)} posts")
```

## Directory Structure

```
Blog/
├── Ready/           # Obsidian notes ready to publish
├── Published/       # Converted Jekyll posts (local copy)
└── Drafts/          # Work-in-progress posts

../chris-jelly.github.io/
└── _posts/          # Blog repository posts directory
```

## Transformation Examples

### Input (Obsidian Note)
```markdown
---
title: My Great Post
categories: [tech, programming]
tags: [python, automation]
date created: 2023-12-01
---

# My Great Post

This post references [[Other Note]] and [[Another Reference]].

Regular markdown content continues here.
```

### Output (Jekyll Post)
```markdown
---
title: My Great Post
date: 2023-12-01 12:00:00 -0400
categories: [tech, programming]
tags: [python, automation]
---

# My Great Post

This post references `Other Note` and `Another Reference`.

Regular markdown content continues here.
```

## Development

### Setup
```bash
git clone https://github.com/chris-jelly/py-obsidian-to-jekyll.git
cd py-obsidian-to-jekyll
uv sync
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=blog_publisher --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_core.py -v
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Lint code  
uv run ruff src/ tests/

# Type checking
uv run mypy src/
```

## Configuration

The tool automatically detects common directory structures:

1. **jelly-brain repository**: Looks for `Blog/Ready/` and `Blog/Published/`
2. **Blog repository**: Searches for `../chris-jelly.github.io/_posts/` or `~/git/chris-jelly.github.io/_posts/`

## License

MIT License - see LICENSE file for details.