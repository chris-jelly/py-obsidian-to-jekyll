## Why

Obsidian wikilinks (`[[Post Title]]`) are currently converted to backtick code spans, making all internal references unclickable on the published blog. Blog readers expect working hyperlinks between related posts, meaningful image embeds for diagrams, and clean prose without code-formatted link artifacts. The existing SVG embed handling also only supports the `.excalidraw` extension and uses relative paths, missing `.svg` direct embeds and the `.excalidraw.svg` naming pattern.

## What Changes

- **New: Post registry** — scan the blog's `_posts/` directory and current Ready/ batch to build a title-to-slug lookup table for cross-post linking.
- **New: Cross-post link resolution** — `[[Post Title]]` matching a registry entry becomes `[Post Title](/posts/post-slug/)` with Jekyll-compatible slug generation.
- **Enhanced: SVG embed handling** — support `![[file.svg]]` in addition to `![[file.excalidraw]]`, search a configurable `--svg-dir`, support `.excalidraw.svg` naming pattern, and output absolute `/assets/` paths.
- **New: Vault-only link fallback** — unresolved `[[links]]` become plain text (no backticks, no formatting) with a warning emitted to help authors catch missed references.
- **New: Link resolution priority** — a defined resolution order: SVG embed → cross-post link → plain text fallback.
- **New: `--svg-dir` CLI option** — configurable SVG source directory with auto-detection of `Excalidraw/` relative to the vault root.
- **BREAKING**: Wikilinks previously rendered as `` `code spans` `` will now render as either hyperlinks, plain text, or image embeds depending on resolution. Existing blog output will change.

## Capabilities

### New Capabilities
- `cross-post-linking`: Post registry building from `_posts/` and Ready/ batch, title matching, and Jekyll-compatible slug-based link generation.
- `svg-embedding`: Enhanced SVG/Excalidraw embed resolution with configurable source directories, multiple naming patterns, and absolute path output.
- `vault-link-fallback`: Plain text conversion for unresolved vault-only links with warning emission.
- `link-resolution`: Priority-ordered link resolution pipeline coordinating SVG embeds, cross-post links, and vault-only fallback.

### Modified Capabilities
_(No existing specs to modify — `openspec/specs/` is empty.)_

## Impact

- **`core.py`**: `convert_obsidian_links()` is rewritten to implement the resolution pipeline instead of the current two-branch (excalidraw vs backtick) logic. `copy_excalidraw_assets()` gains support for additional file patterns and search directories.
- **`cli.py`**: New `--svg-dir` option added; `detect_default_paths()` updated to auto-detect `Excalidraw/` directory.
- **Tests**: Existing wikilink and excalidraw tests will need updating to reflect new behavior. New test classes needed for registry building, cross-post matching, slug consistency, vault-link fallback, and integration scenarios.
- **Blog output**: Published markdown changes for all wikilink types — this is a visible change for any re-published posts.
