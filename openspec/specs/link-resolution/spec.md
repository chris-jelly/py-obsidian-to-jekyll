## Purpose

This capability defines the priority-ordered link resolution pipeline that processes Obsidian wikilinks through multiple resolvers (SVG embed, cross-post, and fallback) and handles code block exclusion.

## Requirements

### Requirement: Priority-ordered link resolution pipeline
The system SHALL process each `[[link]]` and `![[embed]]` through a resolution pipeline in the following fixed order: (1) SVG embed resolver, (2) cross-post link resolver, (3) plain text fallback. The first resolver that produces a result SHALL be used; subsequent resolvers SHALL NOT be invoked for that link.

#### Scenario: SVG embed takes priority over cross-post
- **WHEN** content contains `![[diagram.svg]]` and "diagram.svg" also matches a post title in the registry
- **THEN** the link SHALL be resolved as an SVG embed, not a cross-post link

#### Scenario: Cross-post takes priority over plain text
- **WHEN** content contains `[[My Post Title]]` and the registry contains a matching post
- **THEN** the link SHALL be resolved as a cross-post hyperlink, not converted to plain text

#### Scenario: Plain text as last resort
- **WHEN** content contains `[[Random Note]]` and it matches neither SVG embed nor cross-post criteria
- **THEN** the link SHALL be converted to plain text with a warning

### Requirement: Embed syntax routing
The system SHALL treat `![[...]]` (with exclamation mark) as an embed and `[[...]]` (without) as a link. Embeds with file extensions `.svg` or `.excalidraw` SHALL be routed to the SVG embed resolver. Embeds without recognized extensions SHALL fall through to cross-post and plain text resolution as regular links.

#### Scenario: Embed with svg extension
- **WHEN** content contains `![[file.svg]]`
- **THEN** the SVG embed resolver SHALL handle it

#### Scenario: Embed with excalidraw extension
- **WHEN** content contains `![[file.excalidraw]]`
- **THEN** the SVG embed resolver SHALL handle it

#### Scenario: Regular link with no extension
- **WHEN** content contains `[[Some Post Title]]` (no `!` prefix, no file extension)
- **THEN** the SVG embed resolver SHALL skip it and it SHALL proceed to cross-post resolution

### Requirement: Links inside code blocks are not processed
The system SHALL NOT process wikilinks that appear inside fenced code blocks (``` ``` ```) or inline code spans (`` ` ``). Only wikilinks in regular markdown prose SHALL be resolved.

#### Scenario: Wikilink in fenced code block
- **WHEN** content contains a `[[link]]` inside a fenced code block
- **THEN** the link SHALL be left unchanged

#### Scenario: Wikilink in inline code
- **WHEN** content contains a `[[link]]` inside backtick inline code
- **THEN** the link SHALL be left unchanged
