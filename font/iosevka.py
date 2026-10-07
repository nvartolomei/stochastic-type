#!/usr/bin/env python3
"""Builds the custom Iosevka bases (proportional and monospace, Regular and Bold) from font/iosevka-plan.toml.

Needs node and npm. The checkout and the built fonts stay under build/ (gitignored).
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "iosevka"
OUT = ROOT / "build" / "base"
PLAN = Path(__file__).parent / "iosevka-plan.toml"
REPO = "https://github.com/be5invis/Iosevka"
TARGETS = ["IosevkaStochastic", "IosevkaStochasticMono"]


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    if not (SRC / "package.json").exists():
        SRC.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", REPO, "."], SRC)
    if not (SRC / "node_modules").exists():
        run(["npm", "install", "--no-audit", "--no-fund"], SRC)
    shutil.copy(PLAN, SRC / "private-build-plans.toml")
    shutil.rmtree(SRC / "dist", ignore_errors=True)
    run(["npm", "run", "build", "--", *[f"ttf-unhinted::{t}" for t in TARGETS]], SRC)
    OUT.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        for ttf in (SRC / "dist" / target / "TTF-Unhinted").glob("*.ttf"):
            shutil.copy(ttf, OUT / ttf.name)
    shutil.copy(SRC / "LICENSE.md", OUT / "LICENSE.md")
    shutil.copy(PLAN, OUT / "build-plan.toml")
    print(sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    sys.exit(main())
