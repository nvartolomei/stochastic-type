"""The codepoints the font is subset to: Latin text plus the symbols and terminal graphics
that LLM output and code blocks lean on. No other scripts."""

import unicodedata

BLOCKS = [
    ("Basic Latin", 0x20, 0x7E),
    ("Latin-1", 0xA0, 0xFF),
    ("Latin Ext-A", 0x100, 0x17F),
    ("Latin Ext-B", 0x180, 0x24F),
    ("Modifier letters", 0x2B0, 0x2FF),
    ("Latin Ext Additional", 0x1E00, 0x1EFF),
    ("General Punctuation", 0x2000, 0x206F),
    ("Super/subscripts", 0x2070, 0x209F),
    ("Currency", 0x20A0, 0x20CF),
    ("Letterlike", 0x2100, 0x214F),
    ("Number Forms", 0x2150, 0x218F),
    ("Arrows", 0x2190, 0x21FF),
    ("Math Operators", 0x2200, 0x22FF),
    ("Misc Technical", 0x2300, 0x23FF),
    ("Box Drawing", 0x2500, 0x257F),
    ("Block Elements", 0x2580, 0x259F),
    ("Geometric Shapes", 0x25A0, 0x25FF),
    ("Misc Symbols", 0x2600, 0x26FF),
    ("Dingbats", 0x2700, 0x27BF),
    ("Braille", 0x2800, 0x28FF),
    ("Suppl Arrows-B", 0x2900, 0x297F),
    ("Suppl Math Operators", 0x2A00, 0x2AFF),
    ("Misc Symbols and Arrows", 0x2B00, 0x2BFF),
    ("Legacy Computing", 0x1FB00, 0x1FBFF),
    ("Powerline", 0xE0A0, 0xE0D7),
]

# Glyphs whose exact geometry matters (lines must meet across cells and rows). They are kept as
# the base drew them and are not restyled.
EXACT_BLOCKS = [(0x2500, 0x259F), (0x2800, 0x28FF), (0x1FB00, 0x1FBFF), (0xE0A0, 0xE0D7)]

# Long arrows are drawn two cells wide even in fixed-cell spacing, which would break the grid.
EXCLUDE = set(range(0x27F0, 0x2800)) | {0x2B33}

SKIP_CATEGORIES = {"Cc", "Cf", "Cs", "Cn", "Mn", "Me", "Zl", "Zp"}
PRIVATE_USE_OK = (0xE0A0, 0xE0D7)


def is_exact(cp):
    return any(a <= cp <= b for a, b in EXACT_BLOCKS)


def target_codepoints():
    out = []
    for _, a, b in BLOCKS:
        for cp in range(a, b + 1):
            cat = unicodedata.category(chr(cp))
            if cp in EXCLUDE or cat in SKIP_CATEGORIES:
                continue
            if cat == "Co" and not PRIVATE_USE_OK[0] <= cp <= PRIVATE_USE_OK[1]:
                continue
            out.append(cp)
    return out
