#!/usr/bin/env python3
"""Launcher: `python3 play.py` (or `python play.py` on Windows)."""

import sys

if sys.version_info < (3, 8):
    sys.exit("LocalGames nécessite Python 3.8 ou plus récent.")

from localgames.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
