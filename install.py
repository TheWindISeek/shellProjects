#!/usr/bin/env python3
"""Hook shellProjects/shellrc.sh into ~/.bashrc (conda-style managed block).

Usage:
  python3 install.py           # install / update the block
  python3 install.py uninstall # remove the block
  python3 install.py print     # print the block without writing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BEGIN = "# >>> shellProjects >>>"
END = "# <<< shellProjects <<<"
BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN)}.*?{re.escape(END)}\n?",
    re.DOTALL,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def bashrc_path() -> Path:
    return Path.home() / ".bashrc"


def make_block(root: Path) -> str:
    shellrc = root / "shellrc.sh"
    return (
        f"{BEGIN}\n"
        f'[ -f "{shellrc}" ] && . "{shellrc}"\n'
        f"{END}\n"
    )


def install(bashrc: Path, block: str) -> str:
    text = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
    if BLOCK_RE.search(text):
        new_text = BLOCK_RE.sub(block, text, count=1)
        action = "updated"
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n" + block
        action = "installed"
    bashrc.write_text(new_text, encoding="utf-8")
    return action


def uninstall(bashrc: Path) -> bool:
    if not bashrc.exists():
        return False
    text = bashrc.read_text(encoding="utf-8")
    if not BLOCK_RE.search(text):
        return False
    new_text = BLOCK_RE.sub("", text, count=1)
    # Collapse extra blank lines left by the removed block
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    bashrc.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Install shellProjects into ~/.bashrc")
    parser.add_argument(
        "command",
        nargs="?",
        default="install",
        choices=("install", "uninstall", "print"),
        help="install (default), uninstall, or print",
    )
    args = parser.parse_args()

    root = repo_root()
    shellrc = root / "shellrc.sh"
    if not shellrc.is_file():
        print(f"Missing {shellrc}", file=sys.stderr)
        return 1

    block = make_block(root)
    bashrc = bashrc_path()

    if args.command == "print":
        print(block, end="")
        return 0

    if args.command == "uninstall":
        if uninstall(bashrc):
            print(f"Removed shellProjects block from {bashrc}")
        else:
            print(f"No shellProjects block found in {bashrc}")
        return 0

    action = install(bashrc, block)
    print(f"{'Updated' if action == 'updated' else 'Installed'} in {bashrc}")
    print()
    print(block, end="")
    print()
    print("Tip: remove any old shellProjects aliases still in ~/.bashrc to avoid duplicates.")
    print("     Open a new terminal, or run: source ~/.bashrc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
