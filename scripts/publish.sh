#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/setup-dev.sh

python3 -m pip install -U build twine >/dev/null
rm -rf dist build
python3 -m build
bash scripts/test-install.sh dist/dcad-*.whl

if [[ "${1:-}" == "--upload" ]]; then
  if [[ -z "${PYPI_API_TOKEN:-}" ]]; then
    echo "error: set PYPI_API_TOKEN before running with --upload" >&2
    exit 1
  fi
  python3 -m twine upload dist/*
  echo "Published to PyPI. Users can now run: pipx install dcad"
else
  echo "Built dist/dcad-*.whl (dry run — pass --upload to publish to PyPI)"
fi
