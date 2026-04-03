# Release & Publishing Guide

## One-Time Setup

### 1. SignPath (free code signing for OSS)

1. Go to [SignPath Foundation](https://signpath.org) and click **Apply**
   - You'll need your public GitHub repo URL
   - Approval typically takes 1-3 business days

2. Once approved, in your SignPath dashboard:
   - Note your **Organization ID** (shown in dashboard URL)
   - Create a project named `fnwispr`
   - Create a signing policy named `release-signing`
   - Create an artifact configuration named `default` for signing `.exe` files
   - Generate a **CI User API token**

3. In your GitHub repo, go to **Settings > Secrets and variables > Actions** and add:
   - `SIGNPATH_API_TOKEN` — the CI user API token
   - `SIGNPATH_ORGANIZATION_ID` — your organization ID

4. In SignPath, link your GitHub repository:
   - Go to your project settings
   - Under "Trusted Build Systems", add your GitHub repo
   - This allows SignPath to verify that artifacts came from your CI

### 2. GitHub Repository Settings

Ensure your repo has:
- **Actions enabled** (Settings > Actions > General)
- **Read and write permissions** for workflows (Settings > Actions > General > Workflow permissions)

## Releasing a New Version

### Step 1: Tag and push

```bash
git tag v1.0.0
git push origin v1.0.0
```

This triggers the release workflow which will:
1. Build the PyInstaller bundle on Windows
2. Create an Inno Setup installer
3. Submit to SignPath for code signing
4. Create a **draft** GitHub Release with the signed installer

### Step 2: Review the release

- Go to your repo's Releases page
- Find the draft release
- Edit the release notes if needed
- Click **Publish release** when ready

### Step 3: Submit to winget

After publishing the release:

```bash
# Install wingetcreate if you haven't already
winget install wingetcreate

# Submit to winget-pkgs (first time — creates new package)
wingetcreate new https://github.com/fnrhombus/fnwispr/releases/download/v1.0.0/fnwispr-1.0.0-setup.exe

# For subsequent releases — updates existing package
wingetcreate update fnrhombus.fnwispr --version 1.0.0 \
  --urls https://github.com/fnrhombus/fnwispr/releases/download/v1.0.0/fnwispr-1.0.0-setup.exe \
  --submit
```

`wingetcreate new` will interactively prompt you for package metadata and generate
the manifest YAML files, then open a PR to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).

## Testing Locally

### Build the PyInstaller bundle

```bash
# Generate the .ico from the SVG
python packaging/convert_icon.py

# Build with PyInstaller
cd packaging
pyinstaller fnwispr.spec --noconfirm
cd ..

# The output is in dist/fnwispr/
dist/fnwispr/fnwispr.exe
```

### Build the installer (requires Inno Setup installed)

```bash
iscc /DMyAppVersion=1.0.0 packaging/fnwispr.iss
# Output: dist/fnwispr-1.0.0-setup.exe
```

## File Overview

```
packaging/
  convert_icon.py   — SVG-to-ICO converter (used by CI and local builds)
  fnwispr.spec      — PyInstaller spec (bundles Python + deps into exe)
  fnwispr.iss       — Inno Setup script (wraps bundle into installer)
  RELEASE.md        — This file

.github/workflows/
  release.yml       — CI pipeline: build → sign → release
```
