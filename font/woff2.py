"""Compress a TTF to WOFF2: woff2.py in.ttf out.woff2"""
import sys

from fontTools.ttLib import TTFont

src, dst = sys.argv[1:3]
font = TTFont(src, recalcTimestamp=False)
font.flavor = "woff2"
font.save(dst)
