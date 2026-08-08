#!/usr/bin/env bash
# Third-party deps for shellProjects. Run from repo root or here:
#   bash vendor/runme.sh
# Does not install anything by itself — prints what is missing and how to fetch it.

set -euo pipefail

_VENDOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_ROOT="$(cd "${_VENDOR_DIR}/.." && pwd)"

echo "shellProjects vendor deps"
echo "root: ${_ROOT}"
echo

# ---- rupa/z (directory jumper; sourced by shellrc.sh) ----
_Z_DIR="${_VENDOR_DIR}/z"
_Z_URL="https://github.com/rupa/z.git"
if [ -f "${_Z_DIR}/z.sh" ]; then
  echo "[ok] z  -> ${_Z_DIR}"
else
  echo "[missing] z  (https://github.com/rupa/z)"
  echo "  git clone --depth 1 ${_Z_URL} ${_Z_DIR}"
fi

echo
echo "Optional system packages (apt):"
echo "  sudo apt-get install nload tilix aptitude"
echo
echo "Clash binary (optional, see README): tools/net/Clash/"
echo "Done."
