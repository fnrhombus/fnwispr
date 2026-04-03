---
name: release
description: "Release fnwispr by bumping the version, merging dev into main, and pushing to trigger the CI/CD release workflow. Use this skill whenever the user says 'release', 'ship it', 'cut a release', 'push a release', 'deploy', or wants to merge dev into main for a release."
---

# Release

Automate the fnwispr release process: bump version, merge dev → main, push to trigger the GitHub Actions release workflow.

## Prerequisites

Before starting, verify:
1. You are on the `dev` branch
2. The working tree is clean (no uncommitted changes)
3. All tests pass (if applicable)

If any prerequisite fails, stop and tell the user what needs to be fixed.

## Steps

### 1. Determine the version bump

Ask the user what kind of release this is:
- **patch** (bug fixes, internal changes) — bumps `0.1.0` → `0.1.1`
- **minor** (new features) — bumps `0.1.0` → `0.2.0`
- **major** (breaking changes) — bumps `0.1.0` → `1.0.0`

If the user already specified the bump type (e.g., `/release patch`), use that without asking.

### 2. Bump the version

1. Read the current version from the `VERSION` file in the repo root
2. Apply the semver bump
3. Write the new version back to `VERSION`
4. Commit on `dev` with message: `bump version to X.Y.Z`

### 3. Merge and push

1. `git checkout main`
2. `git merge dev` (fast-forward preferred; if not possible, use a merge commit)
3. `git push origin main` — this triggers the release workflow
4. `git checkout dev` — switch back to the development branch

### 4. Confirm

Tell the user:
- The new version number
- That the push to `main` will trigger the release workflow
- Link them to the Actions tab: `https://github.com/fnrhombus/fnwispr/actions`

## Error handling

- If the merge has conflicts, abort (`git merge --abort`), switch back to `dev`, and tell the user to resolve conflicts manually.
- If the push fails, switch back to `dev` and report the error.
- Always ensure the user ends up back on the `dev` branch, even if something fails.
