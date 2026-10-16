# Design

## Context

- **What the Space stores where** (Hub `paths-info` for the live Space): `Caveat.ttf` (403,648 bytes) and `ReenieBeanie.ttf` (147,036 bytes) are LFS with Xet; `CourierPrime-Regular.ttf` (71,188 bytes) and the sample card PNGs (about 45 KB) are plain git. The upload decides this per file; the repository has no say.
- **The Space's `.gitattributes` is the repository's,** because the bundle is a `git archive` of `HEAD` and so contains it. It has no `filter=lfs` rules, so the Space's build checks out LFS files as pointers.
- **The failure is in the build's checkout, not the upload:** the font downloaded from the Space repo is byte-identical to the repository's.

## Goals / Non-Goals

**Goals:** every committed binary file reaches the Space's container intact, whichever way the upload stores it.

**Non-Goals:** moving the repository itself to LFS, or changing which files the Hub stores in LFS.

## Decisions

### D1. Add LFS rules for the bundle's binary file types
- **Detected from the bundle,** with git's own test for binary content (a NUL byte in the first 8,000 bytes), so a new binary type is covered without editing the script.
- **One rule per extension,** appended after the repository's rules: `*.<ext> filter=lfs diff=lfs merge=lfs -text`.
- **Safe for files stored as plain git:** git-lfs's smudge filter passes through content that isn't an LFS pointer.
- **Alternative considered:** leaving `.gitattributes` out of the bundle to keep the Space's own. The Space's own file was already replaced by earlier deploys, and the Hub's default rules don't cover fonts or images, so it would still need these rules.

### D2. Check the live demo after deploying
- **Verified by hand after the redeploy:** a generated card and the sample cards load from the hosted demo, and the sample cards match the committed files byte for byte.

## Risks / Trade-offs

- [A text file with an extension shared by a binary one] → It would be marked for LFS too. The bundle has none today; git-lfs would pass it through unchanged anyway.
