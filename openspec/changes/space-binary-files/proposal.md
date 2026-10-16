# Proposal

## Why

On the hosted demo, a made-up request's vaccine card fails to load: `/api/demo/generated/<seed>/certificate.png` answers 500 with `OSError: unknown file format` when Pillow opens `Caveat.ttf`. Hugging Face stores larger binary files in LFS (Xet), and here it stored `Caveat.ttf` and `ReenieBeanie.ttf` that way. A Space's build only resolves LFS files that its `.gitattributes` marks for LFS. The deploy bundle carries the repository's `.gitattributes`, which has no LFS rules and replaces the Space's own, so the build checks out those fonts as LFS pointer files. Smaller binaries such as the sample cards are stored as plain git and load. The previous deploy already had the same state, so this predates the latest changes.

## What Changes

- **The deploy bundle marks its binary file types for LFS.** The bundle's `.gitattributes` keeps the repository's rules and adds an LFS rule for each extension that has a binary file in the bundle (today `gif`, `ico`, `jpg`, `png`, `ttf`). Files Hugging Face keeps as plain git are unaffected: git-lfs passes content that isn't a pointer through unchanged.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `demo-hosting`: the deploy bundle's `.gitattributes` marks its binary file types for LFS.

## Impact

- **Deploy:** `backend/scripts/deploy_space.py`.
- **Tests:** a bundle test for the LFS rules.
- **Hosted demo:** redeployed; generated cards load again.
