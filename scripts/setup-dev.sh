#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d packages/cadpy ]]; then
  echo "error: packages/cadpy is missing — vendor cadpy before installing dcad." >&2
  exit 1
fi

if [[ ! -d skills/cad ]]; then
  echo "error: skills/cad is missing — vendor the CAD skill before installing dcad." >&2
  exit 1
fi

mkdir -p skills/cad/scripts/packages
ln -sfn ../../../../packages/cadpy skills/cad/scripts/packages/cadpy

echo "Prepared skills/cad/scripts/packages/cadpy symlink."
