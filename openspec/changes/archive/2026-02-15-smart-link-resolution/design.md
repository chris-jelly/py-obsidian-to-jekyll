## Context

The current `convert_obsidian_links()` function in `core.py:35-71` uses a single regex to match `!?[[...]]` patterns and routes them through a two-branch callback: Excalidraw embeds become markdown images, everything else becomes backtick code spans. There is no awareness of other published posts, no configurable SVG source directory, and no distinction between cross-post references and vault-only notes.

The blog uses the Chirpy Jekyll theme with `permalink: /posts/:title/`, meaning post URLs follow the pattern `/posts/<slug>/` where the slug is derived from the title.

## Goals / Non-Goals

**Goals:**
- Replace the two-branch link handler with a priority-ordered resolution pipeline (SVG embed → cross-post → plain text)
- Build a post registry from existing `_posts/` files and the current Ready/ batch for cross-post link resolution
- Support `.svg`, `.excalidraw`, and `.excalidraw.svg` file patterns for SVG embedding
- Add `--svg-dir` CLI option with auto-detection of `Excalidraw/` directory
- Emit actionable warnings for unresolved vault-only links
- Maintain backward compatibility for Excalidraw embed output (aside from path format change)

**Non-Goals:**
- Full bidirectional link graph or backlinks
- Supporting non-SVG image embeds (PNG, JPEG, etc.)
- Partial/fuzzy title matching for cross-post links
- Processing links inside code blocks or frontmatter
- Supporting Obsidian aliases (`[[target|display text]]`) — this can be a future enhancement

## Decisions

### 1. Resolution pipeline architecture

**Decision**: Replace the inner `convert_link` callback with a chain of resolver functions called in priority order. Each resolver returns either a replacement string or `None` to pass to the next.

**Rationale**: This is more extensible than nested if/else and makes the priority order explicit. Each resolver can be tested independently. The alternative — a single function with many branches — would become harder to maintain as more link types are added.

**Resolution order**: SVG embed → cross-post link → plain text fallback.

### 2. Post registry as a pre-built lookup dict

**Decision**: Build the registry as a `dict[str, str]` mapping `lowercase_title → slug` before processing any links. Build it once per `publish_posts()` invocation by scanning `_posts/` frontmatter and deriving titles/slugs from Ready/ batch files.

**Rationale**: A pre-built dict gives O(1) lookup per link. The alternative — scanning `_posts/` for each link — would be O(n×m). The registry is small (typically <100 posts) so memory is not a concern.

### 3. Slug generation reuse

**Decision**: Extract the existing slug generation logic (`core.py:197-198`) into a standalone `generate_slug(title: str) -> str` function. Use it for both Jekyll filename generation and cross-post URL construction.

**Rationale**: The slug in `/posts/<slug>/` must match what Jekyll generates. Using the same function guarantees consistency. Currently the logic is inline in `convert_post()` — extracting it makes it reusable and independently testable.

### 4. SVG search path order

**Decision**: Search for SVG files in this order:
1. `--svg-dir` (explicit Excalidraw directory)
2. Same directory as the source markdown file
3. `Blog/assets/` in the vault (existing behavior)

**Rationale**: The explicit `--svg-dir` should take priority since the user configured it intentionally. The remaining paths preserve existing behavior as fallbacks. Auto-detection will look for `Excalidraw/` at `vault_root/Excalidraw/` where vault root is the parent of the `Ready/` directory's parent.

### 5. Absolute vs relative SVG paths in output

**Decision**: Change SVG image paths from relative (`assets/file.svg`) to absolute (`/assets/file.svg`).

**Rationale**: The Chirpy theme serves assets from the site root. Absolute paths work regardless of the post's URL depth. The current relative paths only work by coincidence with the current permalink structure.

### 6. Warning output for unresolved links

**Decision**: Use Python's `logging` module at WARNING level rather than `print()` for unresolved link warnings. Format: `WARNING: unresolved link [[Name]] in "Post Title" -- converted to plain text`.

**Rationale**: Using `logging` allows warnings to be captured, filtered, and redirected. The existing codebase uses `print()` for progress output, but warnings are a different concern. This also makes it easy to test warning output by checking log records.

## Risks / Trade-offs

**[Risk] Slug mismatch with Jekyll** → The slug generation must exactly match Jekyll's `:title` parameter behavior. Mitigation: test against known Jekyll-generated URLs. The current regex approach (`[^a-zA-Z0-9\s-]` removal + space-to-hyphen) matches standard Jekyll behavior for ASCII titles.

**[Risk] Performance with large `_posts/` directories** → Scanning and parsing YAML frontmatter for every file in `_posts/` adds startup overhead. Mitigation: for a typical blog (<200 posts), this takes <1 second. No caching needed at this scale.

**[Risk] Breaking change in link output** → Posts previously rendered with `` `link text` `` will now show as plain text or hyperlinks. Mitigation: this is the intended behavior change. Users must re-publish affected posts. The BREAKING flag is noted in the proposal.

**[Trade-off] No fuzzy matching** → Only exact (case-insensitive) title matches produce cross-post links. Near-misses silently become plain text. This is intentional — false positive links are worse than false negatives, and warnings make missed links visible.
