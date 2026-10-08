#!/usr/bin/env python3
"""Renders the README screenshots at 2x from specimen/shots.html into docs/.

    uv run specimen/shots.py

Needs Chrome or Chromium (set CHROME to point at it) and the fonts in dist/.
Each section of shots.html is shown through its #fragment, measured, then captured at its own height.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "specimen" / "shots.html"
OUT = ROOT / "docs"
SHOTS = ["sans", "mono", "chars", "sizes"]
WIDTH = 880
SCALE = 2
CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


def chrome():
    for candidate in [os.environ.get("CHROME"), *CANDIDATES]:
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    sys.exit("Chrome or Chromium not found; set CHROME")


def run(browser, *args):
    base = [browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000"]
    return subprocess.run(base + list(args), capture_output=True, text=True, check=True)


def height(browser, name):
    dom = run(browser, "--dump-dom", f"--window-size={WIDTH},1000", f"{PAGE.as_uri()}#{name}").stdout
    found = re.search(r'data-height="(\d+)"', dom)
    if not found:
        sys.exit(f"could not measure #{name}")
    return int(found.group(1))


def main():
    browser = chrome()
    OUT.mkdir(exist_ok=True)
    for name in SHOTS:
        h = height(browser, name)
        target = OUT / f"{name}.png"
        run(browser, f"--force-device-scale-factor={SCALE}", f"--window-size={WIDTH},{h}",
            f"--screenshot={target}", f"{PAGE.as_uri()}#{name}")
        print(f"{target.relative_to(ROOT)}  {WIDTH * SCALE}x{h * SCALE}")


if __name__ == "__main__":
    main()
