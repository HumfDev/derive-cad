#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <dcad-wheel-path>" >&2
  exit 1
fi

WHEEL="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$(mktemp -d)/test-install-venv"

python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install -U pip wheel >/dev/null
python -m pip install "$WHEEL"

dcad --version
dcad --help >/dev/null

python - <<'PY'
import cadpy
import derive_cad
from derive_cad.skill.paths import repo_root

root = repo_root()
assert (root / "skills" / "cad" / "SKILL.md").is_file(), root
assert (root / "packages" / "cadpy").is_dir(), root
print("skills/cad and packages/cadpy present at", root)
PY

echo "Install smoke test passed for $WHEEL"
