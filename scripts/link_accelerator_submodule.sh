#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pytorch-fdn/accelerator-integration-wg.git"
SUBMODULE_PATH="third_party/accelerator-integration-wg"

if git submodule status -- "$SUBMODULE_PATH" >/dev/null 2>&1; then
  echo "Submodule already exists at $SUBMODULE_PATH"
  exit 0
fi

mkdir -p third_party

echo "Adding submodule: $REPO_URL -> $SUBMODULE_PATH"
git submodule add "$REPO_URL" "$SUBMODULE_PATH"

echo "Syncing and initializing submodule"
git submodule sync --recursive
git submodule update --init --recursive

echo "Done"
