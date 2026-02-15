## 1. Extract and refactor shared utilities

- [x] 1.1 Extract `generate_slug(title: str) -> str` function from inline logic in `convert_post()` (core.py:197-198) into a standalone function
- [x] 1.2 Update `convert_post()` to call `generate_slug()` for Jekyll filename generation
- [x] 1.3 Add tests for `generate_slug()` covering special characters, consecutive spaces, unicode, and empty input

## 2. Post registry

- [x] 2.1 Implement `build_post_registry(posts_dir: Path, ready_files: list[Path]) -> dict[str, str]` that scans `_posts/` frontmatter and Ready/ batch files, returning lowercase_title → slug mapping
- [x] 2.2 Handle edge cases: missing title frontmatter (skip), duplicate titles (most recent wins), empty directories
- [x] 2.3 Add tests for registry building from `_posts/`, Ready/ batch inclusion, missing titles, and duplicates

## 3. Link resolution pipeline

- [x] 3.1 Implement SVG embed resolver: detect `![[file.svg]]`, `![[file.excalidraw]]` patterns and return markdown image with absolute `/assets/` path
- [x] 3.2 Support `.excalidraw.svg` naming pattern — when `![[file.excalidraw]]` is encountered, check for both `file.svg` and `file.excalidraw.svg`
- [x] 3.3 Implement cross-post link resolver: look up `[[link text]]` in registry, return `[Title](/posts/slug/)` or None
- [x] 3.4 Implement vault-only fallback resolver: return plain text (no backticks) and emit WARNING-level log message with format `unresolved link [[Name]] in "Post Title" -- converted to plain text`
- [x] 3.5 Implement pipeline coordinator: process each `!?[[...]]` match through resolvers in order (SVG → cross-post → fallback), using first non-None result
- [x] 3.6 Add code block exclusion: skip wikilinks inside fenced code blocks and inline code spans
- [x] 3.7 Rewrite `convert_obsidian_links()` to use the new pipeline, accepting registry and post title as parameters

## 4. SVG file handling enhancements

- [x] 4.1 Update `copy_excalidraw_assets()` to support `.svg` direct embeds and `.excalidraw.svg` naming pattern in file search
- [x] 4.2 Add `svg_dir` parameter to search path — insert as first location in the search order
- [x] 4.3 Change SVG image paths in output from relative `assets/` to absolute `/assets/`
- [x] 4.4 Add tests for SVG search order, `.excalidraw.svg` pattern, and missing file warnings

## 5. CLI integration

- [x] 5.1 Add `--svg-dir` option to CLI with `click.Path` type
- [x] 5.2 Update `detect_default_paths()` to auto-detect `Excalidraw/` directory at vault root (parent of Ready/ directory's parent)
- [x] 5.3 Wire `svg_dir` through to `publish_posts()` and `convert_post()`
- [x] 5.4 Wire post registry building into `publish_posts()` — build once before processing files

## 6. Update existing tests

- [x] 6.1 Update `TestConvertObsidianLinks` tests to expect new behavior (plain text instead of backtick code spans for unresolved links)
- [x] 6.2 Update `TestExcalidrawConversion` tests to expect absolute `/assets/` paths
- [x] 6.3 Update `TestConvertPost` and `TestIntegration` to pass registry and validate new link output

## 7. New tests

- [x] 7.1 Add `TestCrossPostLinking` — registry lookup, case-insensitive matching, slug generation consistency
- [x] 7.2 Add `TestVaultLinkFallback` — plain text output, warning log emission, no warnings for resolved links
- [x] 7.3 Add `TestLinkResolutionPipeline` — priority order (SVG > cross-post > fallback), embed syntax routing, code block exclusion
- [x] 7.4 Add integration test — multi-post batch with cross-references and SVG embeds verifying all link types resolve correctly in a single run
