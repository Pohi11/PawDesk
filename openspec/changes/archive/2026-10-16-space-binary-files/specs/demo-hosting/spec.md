# Spec Delta

## MODIFIED Requirements

### Requirement: A deploy publishes only committed files
The deploy bundle SHALL contain exactly the files committed at `HEAD`, with the Space's Dockerfile and README in place of the repository's root ones. Uncommitted files, ignored files (such as `.env`), and private working notes SHALL never be included. The bundle's `.gitattributes` SHALL keep the repository's rules and mark every file extension that has a binary file in the bundle for LFS, so files the Hub stores in LFS are resolved when the Space builds.

#### Scenario: Bundle contents
- **WHEN** the deploy bundle is built from a checkout that also has `.env` and an untracked file
- **THEN** the bundle holds the committed files plus the Space Dockerfile and README, and neither `.env` nor the untracked file

#### Scenario: Binary files marked for LFS
- **WHEN** the deploy bundle is built from a commit with a font, a PNG, and text files
- **THEN** the bundle's `.gitattributes` keeps the repository's rules and marks `*.ttf` and `*.png` for LFS, and marks no text file's extension
