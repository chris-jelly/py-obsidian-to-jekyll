## ADDED Requirements

### Requirement: SVG embed syntax support
The system SHALL recognize `![[filename.svg]]` as an SVG embed in addition to the existing `![[filename.excalidraw]]` syntax. Both patterns SHALL produce a markdown image reference in the output.

#### Scenario: Direct SVG embed
- **WHEN** content contains `![[diagram.svg]]`
- **THEN** the output SHALL be `![diagram](/assets/diagram.svg)`

#### Scenario: Legacy excalidraw embed
- **WHEN** content contains `![[diagram.excalidraw]]`
- **THEN** the output SHALL be `![diagram](/assets/diagram.svg)`

#### Scenario: Excalidraw.svg naming pattern
- **WHEN** content contains `![[diagram.excalidraw]]` and the source file is named `diagram.excalidraw.svg`
- **THEN** the system SHALL find and copy `diagram.excalidraw.svg` and output `![diagram](/assets/diagram.excalidraw.svg)`

### Requirement: Absolute asset paths
The system SHALL output SVG image references with absolute paths (`/assets/filename.svg`) rather than relative paths (`assets/filename.svg`).

#### Scenario: Image path format
- **WHEN** an SVG embed is resolved
- **THEN** the markdown image path SHALL start with `/assets/`

### Requirement: Configurable SVG source directory
The system SHALL accept a `--svg-dir` CLI option specifying the directory to search for SVG source files. When not provided, the system SHALL auto-detect the `Excalidraw/` directory relative to the vault root (parent of the Ready/ directory's parent).

#### Scenario: Explicit svg-dir option
- **WHEN** the user provides `--svg-dir /path/to/excalidraw`
- **THEN** the system SHALL search that directory first when resolving SVG embeds

#### Scenario: Auto-detection of Excalidraw directory
- **WHEN** `--svg-dir` is not provided and an `Excalidraw/` directory exists at the vault root
- **THEN** the system SHALL use that directory as the SVG source

#### Scenario: No svg-dir found
- **WHEN** `--svg-dir` is not provided and no `Excalidraw/` directory is found
- **THEN** the system SHALL fall back to searching only the markdown file's directory and `Blog/assets/`

### Requirement: SVG file search order
The system SHALL search for SVG files in the following order: (1) the configured `--svg-dir`, (2) the same directory as the source markdown file, (3) `Blog/assets/` in the vault. The first match SHALL be used.

#### Scenario: File found in svg-dir
- **WHEN** the SVG file exists in `--svg-dir` and also in the markdown file's directory
- **THEN** the copy from `--svg-dir` SHALL be used

#### Scenario: File found in markdown directory
- **WHEN** the SVG file does not exist in `--svg-dir` but exists in the markdown file's directory
- **THEN** the copy from the markdown file's directory SHALL be used

#### Scenario: File not found anywhere
- **WHEN** the SVG file is not found in any search location
- **THEN** the system SHALL emit a warning and still produce the image reference in the output

### Requirement: SVG file copy to blog assets
The system SHALL copy resolved SVG files to the blog's assets directory. If the source and target are the same file, no copy SHALL occur.

#### Scenario: Successful copy
- **WHEN** an SVG file is found and the blog assets directory is configured
- **THEN** the file SHALL be copied to the blog assets directory

#### Scenario: Idempotent copy
- **WHEN** the SVG file already exists at the target location with the same content
- **THEN** the system SHALL overwrite with `shutil.copy2` (preserving metadata) without error
