#!/usr/bin/env bash
set -eo pipefail

readonly REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "=== Initializing Custom Agent Environment"
echo "========================================="

if command -v apt-get &> /dev/null; then
    echo "--> Installing system package dependencies..."
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends \
        curl wget git jq build-essential ca-certificates gnupg unzip htop net-tools
fi

if [ -n "${GIT_AUTHOR_NAME:-}" ] && [ -n "${GIT_AUTHOR_EMAIL:-}" ]; then
    echo "--> Configuring Git identity..."
    git config --global user.name "$GIT_AUTHOR_NAME"
    git config --global user.email "$GIT_AUTHOR_EMAIL"
fi
git config --global init.defaultBranch main
git config --global pull.rebase false

if command -v npm &> /dev/null; then
    echo "--> Setting up Node package managers..."
    npm install -g pnpm yarn --quiet
fi

if command -v python3 &> /dev/null; then
    echo "--> Installing zWorkforce from $REPOSITORY_ROOT..."
    python3 -m pip install --upgrade pip setuptools wheel --quiet
    python3 -m pip install "$REPOSITORY_ROOT" --quiet
fi

if [ -f "$REPOSITORY_ROOT/packages/zarvis/pnpm-lock.yaml" ] && command -v pnpm &> /dev/null; then
    echo "--> Installing ZARVIS workspace dependencies..."
    pnpm --dir "$REPOSITORY_ROOT/packages/zarvis" install --frozen-lockfile
fi

echo "========================================="
echo "=== Custom Environment Ready!"
echo "========================================="
