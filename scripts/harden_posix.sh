#!/usr/bin/env sh
set -eu
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
mkdir -p "$PROJECT_ROOT/private" "$PROJECT_ROOT/workspace"
chmod 700 "$PROJECT_ROOT/private" "$PROJECT_ROOT/workspace"
find "$PROJECT_ROOT/private" -type f -exec chmod 600 {} \;
if [ -f "$PROJECT_ROOT/.env" ]; then
  chmod 600 "$PROJECT_ROOT/.env"
else
  echo "Skipped .env permissions because the file does not exist yet. Run this script again after saving DeepSeek settings."
fi
echo "Private paths and .env are restricted to the current OS user."
