## Purpose

This capability enables automatic linking between blog posts by building a post registry and resolving wikilinks that match post titles to Jekyll-compatible hyperlinks.

## Requirements

### Requirement: Post registry building
The system SHALL build a post registry by scanning the blog's `_posts/` directory, extracting the `title` field from each post's YAML frontmatter. The registry SHALL also include all markdown files in the current Ready/ batch, deriving titles from their frontmatter. The registry SHALL map lowercase titles to their corresponding URL slugs.

#### Scenario: Registry from existing blog posts
- **WHEN** the blog's `_posts/` directory contains files with YAML frontmatter including a `title` field
- **THEN** the registry SHALL contain an entry for each post mapping its lowercase title to its slug

#### Scenario: Registry includes current batch
- **WHEN** the Ready/ directory contains markdown files with `title` in their frontmatter
- **THEN** the registry SHALL include those titles so posts published together can cross-reference each other

#### Scenario: Posts without title frontmatter
- **WHEN** a file in `_posts/` has no `title` field in its frontmatter
- **THEN** that file SHALL be skipped and not included in the registry

#### Scenario: Duplicate titles
- **WHEN** multiple posts have the same title (case-insensitive)
- **THEN** the most recently dated post SHALL take precedence in the registry

### Requirement: Cross-post link resolution
The system SHALL convert `[[link text]]` wikilinks to standard markdown hyperlinks when the link text matches a title in the post registry (case-insensitive). The output format SHALL be `[Original Title](/posts/slug/)`.

#### Scenario: Exact title match
- **WHEN** content contains `[[Part 1 - Airflow on K8s Introduction]]` and the registry contains a post with that title
- **THEN** the output SHALL be `[Part 1 - Airflow on K8s Introduction](/posts/part-1---airflow-on-k8s-introduction/)`

#### Scenario: Case-insensitive matching
- **WHEN** content contains `[[my post title]]` and the registry contains a post titled "My Post Title"
- **THEN** the link SHALL resolve using the registry entry's slug, preserving the original link text as display text

#### Scenario: No match in registry
- **WHEN** content contains `[[Some Note]]` and no registry entry matches
- **THEN** the link SHALL NOT be converted to a hyperlink and SHALL fall through to the next resolver

### Requirement: Slug generation function
The system SHALL provide a standalone `generate_slug(title: str) -> str` function that produces URL slugs matching Jekyll's `:title` permalink parameter. The function SHALL lowercase the title, remove characters that are not alphanumeric, spaces, or hyphens, and replace spaces with hyphens.

#### Scenario: Standard title
- **WHEN** the input title is "Part 1 - Airflow on K8s Introduction"
- **THEN** the slug SHALL be `part-1---airflow-on-k8s-introduction`

#### Scenario: Special characters removed
- **WHEN** the input title contains characters like `&`, `@`, `!`, or `.`
- **THEN** those characters SHALL be removed from the slug

#### Scenario: Consecutive spaces
- **WHEN** the input title contains multiple consecutive spaces
- **THEN** they SHALL be collapsed to a single hyphen in the slug
