## ADDED Requirements

### Requirement: Plain text conversion for unresolved links
The system SHALL convert unresolved `[[link text]]` wikilinks to plain text — the link text without any formatting, brackets, or backticks. This applies to links that are not matched by SVG embed resolution or cross-post link resolution.

#### Scenario: Simple unresolved link
- **WHEN** content contains `[[Concept Diagram]]` and it does not match any SVG embed or cross-post title
- **THEN** the output SHALL be `Concept Diagram` (plain text, no backticks, no brackets)

#### Scenario: Unresolved link with special characters
- **WHEN** content contains `[[My Note (Draft)]]` and it is unresolved
- **THEN** the output SHALL be `My Note (Draft)` (plain text preserving the original text)

#### Scenario: Multiple unresolved links in one post
- **WHEN** content contains `[[Note A]]` and `[[Note B]]` and neither resolves
- **THEN** both SHALL be converted to plain text independently

### Requirement: Warning emission for unresolved links
The system SHALL emit a warning for each unresolved wikilink, including the link text and the post title. The warning SHALL use Python's `logging` module at WARNING level. The format SHALL be: `unresolved link [[<link text>]] in "<post title>" -- converted to plain text`.

#### Scenario: Warning format
- **WHEN** `[[Kubernetes]]` is unresolved in a post titled "My Blog Post"
- **THEN** a WARNING-level log message SHALL be emitted: `unresolved link [[Kubernetes]] in "My Blog Post" -- converted to plain text`

#### Scenario: No warning for resolved links
- **WHEN** a wikilink is successfully resolved as a cross-post link or SVG embed
- **THEN** no warning SHALL be emitted for that link
