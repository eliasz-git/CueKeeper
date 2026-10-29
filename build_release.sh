#!/bin/bash
# build_release.sh — Tag and create a GitHub release for CueKeeper.
# Usage: ./build_release.sh <version> [--skip-release]
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION="${1:?Usage: ./build_release.sh <version> [--skip-release]}"
SKIP_RELEASE="${2:-}"

cd "$PROJECT_DIR"

# Version must match __version__ in src/main.py and package.json.
MAIN_VER=$(python3 -c "import re; print(re.search(r'__version__ = \"([^\"]+)\"', open('src/main.py').read()).group(1))")
PKG_VER=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")
if [ "$MAIN_VER" != "$VERSION" ] || [ "$PKG_VER" != "$VERSION" ]; then
  echo "ERROR: version mismatch — main.py=$MAIN_VER package.json=$PKG_VER requested=$VERSION"
  echo "       Update __version__ in src/main.py and version in package.json first."
  exit 1
fi

echo "==> Running checks..."
ruff check src tests || { echo "RUFF FAILED"; exit 1; }
pytest -q || { echo "PYTEST FAILED"; exit 1; }

echo "==> Checks passed. Version $VERSION is consistent across src/main.py and package.json."

if [ "$SKIP_RELEASE" = "--skip-release" ]; then
  echo "==> Skipping GitHub release creation (--skip-release passed)."
  echo "==> Tagging and pushing v$VERSION (release artifacts can be added via gh release create later)."
else
  echo "==> Creating GitHub release v$VERSION..."
  git tag -d "v$VERSION" 2>/dev/null || true
  git push origin --delete "v$VERSION" 2>/dev/null || true

  gh release create "v$VERSION" \
    --title "CueKeeper $VERSION" \
    --notes "CueKeeper $VERSION

## Bundles
- Source-only release. Run: pip install -r requirements.txt && uvicorn src.main:app

## What's changed
- See git log since previous release.

## Notes
- CueKeeper is LAN-first show control. Set CUEKEEPER_TOKEN before deploying on a shared network.
- Source: https://github.com/tundra-node/CueKeeper"
fi

echo "==> Tagging v$VERSION..."
git tag -d "v$VERSION" 2>/dev/null || true
git push origin --delete "v$VERSION" 2>/dev/null || true

git tag "v$VERSION"
git push origin "v$VERSION"

if [ "$SKIP_RELEASE" != "--skip-release" ]; then
  echo "==> Done. Release v$VERSION created."
else
  echo "==> Done. Tag v$VERSION pushed (GitHub release creation skipped)."
fi