# Stochastic Type: specification

Status: working draft 0.3. This describes what is built, why, and what is still open.

## 1. Purpose

Stochastic Type is a font family for content published by LLMs, "a font built by a stochastic parrot". Two jobs:

1. **Long prose must be comfortable to read.** This outranks every stylistic goal. Where a stylistic idea (squares, machine geometry) conflicted with reading comfort, comfort won.
2. **The text should look recognisably machine-made** without being tiring: a double-storey `a`, a single-storey `g`, a straight `y`, a slashed zero, squarish but not boxy bowls, flat terminals, wide letter bodies.

## 2. Deliverables

| File | What |
|---|---|
| `dist/StochasticSans-{Regular,Bold}.ttf` | Proportional family, for prose and headings |
| `dist/StochasticMono-{Regular,Bold}.ttf` | Monospace family, for code, tables and terminal graphics |
| `dist/specimen.html` | Static page (no build step beyond a copy) that loads the four fonts from its own directory |
| `dist/OFL.txt` | Licence |

Constraints chosen by the owner: **static fonts only** (no variable font), **TTF only** (no WOFF or WOFF2, no per-script subsets), **no italic** (browsers synthesize a slant), **no ligatures**. Naming: superfamily *Stochastic Type* (repository `stochastic-type`); families *Stochastic Sans* and *Stochastic Mono*; PostScript names `StochasticSans-Regular` and so on.

## 3. Character set

Defined by `font/charset.py`, about 3,700 requested codepoints, 3,084 present in the fonts (the base lacks some).

- **Text:** Basic Latin, Latin-1, Latin Extended-A and -B, Latin Extended Additional (Vietnamese), modifier letters.
- **Symbols:** general punctuation, super/subscripts, currency, letterlike, number forms, arrows, math operators and supplemental operators, miscellaneous technical, geometric shapes, miscellaneous symbols, dingbats, miscellaneous symbols and arrows, supplemental arrows-B.
- **Drawing and terminal graphics:** box drawing, block elements, Braille patterns, symbols for legacy computing, Powerline (U+E0A0 to U+E0D7, 22 of 56 exist in the base).
- **Dropped on purpose:** Greek, Cyrillic and every other non-Latin script (owner decision), emoji, and the long arrows U+27F0 to U+27FF and U+2B33. The long arrows are drawn two cells wide even in fixed-cell spacing, which would break the monospace grid. Greek letters used as math symbols (Δ, π, μ) fall back to the system font.

Everything not covered falls back to the reader's system font.

## 4. Metrics, weights and naming records

- 1000 units per em. x-height 504, cap height 690, ascender 715 (set in the Iosevka plan).
- Line box 1.2 em on every platform: typo and hhea ascender 920, descender -280, line gap 0, `USE_TYPO_METRICS` set. Windows clip metrics cover the tallest and deepest glyph (about 1150 and 430).
- Stem targets: Regular 76, Bold 118 units (`TARGET_STEM`).
- Hinting is removed (`fpgm`, `prep`, `cvt `, `DSIG`); `gasp` asks for smoothing at all sizes.
- Name records are rewritten for both families; the Iosevka copyright line is kept and a modification note is added.

## 5. Build pipeline

Entry point: `make` (see section 9). Source files are in `font/`.

1. **Base**: `iosevka-plan.toml` and `iosevka.py` build two custom Iosevka fonts from source with Node: a quasi-proportional sans and a `term` monospace, Regular and Bold, upright only, ligatures off. Shared variants: `f` flat-hook-serifless-crossbar-at-x-height, `t` flat-hook, `g` single-storey-flat-hook-serifless, `y` straight-serifless, `r` flat-top-serifless, capital `I` serifed, `zero` slashed, `one` base, `e` flat-crossbar. Sans: `a` double-storey-flat-bottom-serifless, `i` serifless, `l` semi-tailed, `j` flat-hook-serifless. Mono: `a` double-storey-serifless, `i` serifed, `l` serifed-flat-tailed, `j` flat-hook-serifed (anchored, see section 8). Metric overrides: cap 690, ascender 715, x-height 504, leading 1200. The proportional plan has cell width 530 and sidebearings x0.7 (wide bodies; advances are replaced later). The monospace plan has cell 550 and default sidebearings, plus a flat-top `W` and `w` (section 8).
2. **Subset and scale** (`build.py`): keep only the codepoints in the charset, scale to x-height 504 (a no-op for these bases). Then `hooks.py` evens out the hooks and the arm of `r`, and `marks.py` lightens the dots of the sentence marks (section 6). The base stem is measured as the ink width of `l` at mid-height (y = 230), where serifs, flags and tails do not reach; measuring the bounding box instead made serifed variants look like 400-unit stems.
3. **Spacing** (`spacing.py`, proportional only): section 7.
4. **Restyle** (`restyle.py`, `squarify.py`, `outline.py`), per simple glyph:
   - Thicken or thin to the target stem with a stroke offset (miter joins).
   - **Squircle push** (`squircle_n = 3.2`, where 2 is a circle): each curved run is sampled, its curvature estimated and smoothed, and every sample displaced along its outward normal by `(2^(0.5 - 1/n) - 1) x radius x sin^2(2 x normal angle)`, with the radius capped at 260 and a taper over the first and last 90 units of an open run. Nothing moves where the tangent is axis-aligned. The displaced samples are refitted with quadratic curves, two per original curve. A segment counts as curved if its control points sit more than 5 units from its chord (2.5 for cubics). The base splits many long curves (digits, `S`, `&`) into short, nearly flat quadratics, so only the tightest turns of those qualify. A run that ends against a smooth non-line neighbour is therefore left as drawn: pushing part of one continuous curve leaves a kink where the push stops (it showed as lumps on `2 3 6 9 & c R C`). Runs that end at a corner or a straight line are pushed as before.
   - **Closing** (morphological, radius 7) fills slivers narrower than 14 units. For `W w M m` in the monospace font the radius is 22 so the slivers between their strokes fill like ink traps.
   - **Snap**: straight segments within 7 degrees of vertical or 5 degrees of horizontal (and at least 60 units long) become exactly vertical or horizontal.
   - **Fit**: the result is scaled back into the original bounds on any axis where the original extent is at least 250 (x) or 300 (y), so vertical metrics and alignment hold. A glyph whose restyled area differs from the thickened outline by more than 20 to 25 percent keeps the thickened outline (logged).
   - **Exemptions**: brackets (Unicode Ps and Pe) skip the squircle push, because a long gentle arc has its tangent near 45 degrees for most of its length and the push flares its ends. Box drawing, block elements, Braille, legacy-computing and Powerline glyphs are not restyled at all, so lines keep meeting exactly across cells and rows.
   - Composite glyphs are not touched; their components are restyled and keep their extents, so accents and mark offsets stay valid.
5. **Finish**: remove hinting tables, clear per-point flag bits other than on-curve on every simple glyph (browser sanitizers reject the base's overlap bits on glyphs kept as drawn), recompute bounds and left sidebearings, set line metrics, rename.
6. **Monospace only**: `tuck.py` (section 8).

## 6. Design decisions and the reasons for them

- **Iosevka as the base.** It is generated from code and parameters, it is OFL, it has a monoline construction that survives restyling, and it ships the symbol, box-drawing and Braille coverage we need. A base with stroke contrast was tried first and failed: thinning every stem by a fixed amount nearly erased its crossbars.
- **Restyle in place.** Keeping the base's glyph set, composites and metrics means nothing else has to be rebuilt. The restyle only moves outlines.
- **Squircle push, not a re-draw.** It only displaces points, so it cannot change a glyph's topology. An octagonal-bowl fitter and a centerline-and-pen redraw were both prototyped; the first broke junction-heavy glyphs and the second was rough on this base. Neither is in the repo.
- **Spacing from outlines.** Iosevka centres every letter in a near-uniform cell, which leaves `l`, `f`, `t` and `r` floating. Owner feedback was that tighter side bearings made letters hard to tell apart and that more air reads better, so spacing is computed from each outline instead of tightened (section 7).
- **Double-storey `a`, flat-bottom in the sans.** The first builds used a single-storey `a`; the owner asked for the other style, so `a` is double-storey in both fonts. Once `t`, `f`, `j` and `r` ended in flat L-turns the round-footed `a` no longer fitted, and its curled top ear cannot be changed: in Iosevka the ear variants (flat-top, top-cut, earless) exist for the single-storey `a` only. What can change is the foot. Flat-bottom, tailed, toothless-corner and toothless-rounded were built and the owner picked flat-bottom for the sans: the bowl and the stem end on one flat line, which is the same flat horizontal as the feet of `t` and `l`. The base sits on `l`'s bottom (8 units below the baseline, like the round letters, as for `t`); at 0 a flat base next to round letters looks lifted. The mono `a` keeps the serifless foot until the owner asks for the same; its flat-bottom version is built and looked fine. The tailed double-storey `a` was compared earlier and not chosen.
- **Semi-tailed `l` in the sans.** A short tail tells `l`, `I` and `1` apart, which a plain `l` does not (next to `|` it is nearly the same bar), and makes `l` about as wide as `j`. A narrow `j` has a shorter hook, so it hangs less into the previous letter.
- **`f` crossbar level with `t`.** In the first builds `f`'s bar sat about 44 units (Bold 40) below `t`'s, so in `ft`, `tf`, `fft`, `after`, `often` and `left` the bars stepped. Iosevka's `crossbar-at-x-height` variant puts `f`'s bar at the same height as `t`'s (436 to 500 Regular, 404 to 504 Bold).
- **One L-turn for `l`, `t`, `f`, `j` (`hooks.py`).** The owner liked the foot of the sans `l` (a short flat L-turn) and asked for `t`, `f` and `j` to match. In Iosevka's round hook variants `t` and `j` end in a curl that rises (foot 266 and 226 units against `l`'s 102) while `l` ends in a flat cut, so the sans had two terminal vocabularies. `t`, `f` (top hook) and `j` now use Iosevka's flat-hook variants, and `g` its flat hook, which end in the same flat cut. Iosevka makes a flat hook as long as the crossbar's arm (foot of `t` 190, top hook of `f` 176), so the build cuts `t`, `f` and `j` back to `l`'s measured reach (102 in the sans Regular, 85 Bold, 159 and 139 in the mono, within 3 units in every font). `g` keeps its natural hook, which wraps the bowl. The cut is a vertical line across a flat end, so no curve is touched.
- **Shorter crossbars.** The flat-hook variants also draw longer bars (the mono `t` bar came out 459 units, wider than an `n` at 398), and next to cut hooks the bars looked long. The arms of both bars are cut to a multiple of `l`'s reach: 1.0 left and 1.3 right in the sans (bar 314 Regular, 311 Bold), 0.72 and 1.0 in the mono (350 and 356), where `l`'s tail is much longer.
- **`t` and `a` feet on `l`'s baseline.** The round `t` overshot the baseline by 8 units like `a`, `o` and the tail of `l`; the flat-hook `t` sat on 0 and looked lifted in `That`. Its foot is lowered by 8 (fading out over the next 130 units so the stem keeps its shape), and so is the flat base of the sans `a`. The mono `l` is flat at 0, so the mono `t` stays at 0, and the mono `a` has a round bowl that already overshoots.
- **A flat-top `r` in both families (`hooks.py`).** The sans `r` was Iosevka's compact variant (arm 0.77 of the shoulder of `n`) and the mono the normal one (0.88). The owner asked for a shorter sans arm, and for the two to match, with a terminal that rhymes with the hooks of `l`, `t`, `f` and `j`. Iosevka's flat-top `r` has a rounded corner into a flat run, the same gesture as the top of `f`, and ends in a curl; its proportions are the same in both cells (arm 0.89 of the shoulder of `n` in the sans, 0.87 in the mono), which is the harmony: one variant, no per-family guesswork. Shortening the sans arm went through two versions. First the arm was cut at its end with a vertical line, which left a slanted stub that curls down and relates to nothing else; the same cut applied to a narrow-hook `r` in the mono also made it 0.72 of an `n`, which looked small in a cell where every other letter fills its width. Now a slice is taken out of the middle of the flat run (the top edge stays flat for about 125 units past the stem before the curl starts) and the tip is moved back against the rest, so the curl is whole: the sans arm is 0.72 of the shoulder of `n` (236 units Regular, 211 Bold, against 258 before) and the mono keeps its whole arm (264 and 243). 0.84 was barely different and 0.72 is as short as the curl allows. Corner-hooked, earless-corner and hookless variants were built and looked less like the hooks. `rn` still reads as two letters: the arm ends before the stem of `n`.
- **Lighter sentence marks (`marks.py`).** The period and colon dots were 153 units in the Regular, twice the 76-unit stroke, because Iosevka sizes dots against its own stem; the semicolon stacks one of those on a comma and read as the heaviest thing on a line. The dots and comma heads of `. , : ; ! ?` (and `¡ ¿ … ‥ ‼ ⁇ ⁈ ⁉ ‽`) are scaled to 1.6 stems after the stem change: 121 units in the Regular and 188 in the Bold (the Bold was already lighter, 200). The colon and semicolon are composites with U+A78F, the dot at x-height, which is scaled too. 1.4 looked faint in running text and 1.8 still heavy. This happens before spacing, so sidebearings follow the smaller dots.
- **Weights.** Regular is deliberately medium (76) for screen prose. Bold (118) is tuned so counters in `e` and `a` stay open at body sizes.
- **No synthesized weights.** With only Regular available, the test browser rendered bold text as plain Regular, so both weights ship.

## 7. Proportional spacing (`spacing.py`, `letterspace`)

For each text glyph the left and right ink edges are measured over its zone (x-height for lowercase, cap height for capitals, its own height for punctuation and symbols; digits are handled separately, below). A side's *depth* is how far the outline recedes from its outermost point on average (clipped at 30 percent of the zone height).

- Sidebearing per side = `target - strength x depth`, floored at 14. `target` 80, `strength` 0.6 (letters); 0.8 x target and 0.6 x strength for punctuation and symbols.
- Straight sides therefore get the most room; receding sides (`t f r v y w`) get less.
- Ink on the right keeps at least 24 units of clearance. On the left a descender hook may overhang the previous cell by up to 90 units, so a `j` sits by its stem and not by its tail (before this, the whole glyph was shifted right to clear the hook, leaving 295 units of optical air on its left against a typical 80).
- Digits are tabular: one advance equal to the widest digit plus 62 on each side.
- The space is 360 units.
- Accented composites take their base letter's advance, and their accent components shift with the base.

### 7.1 Pair kerning (`kerning.py`, proportional only)

Per-glyph sidebearings give every letter the same optical bearing, so in the model every pair has the same optical gap (the median, 161 units). A floor, a hook, or a depth model that is off leaves outliers (`T Y F L J f j r`). Kerning is class pair positioning in a `kern` feature: each pair's optical gap is the first glyph's right bearing plus the second's left bearing, glyphs are bucketed by bearing in 4-unit steps, and each class pair gets `-0.7 x (gap - median)`, clamped to -70..+25 units, rounded to 2, and dropped if smaller than 8. About 2,800 class pairs. In the model the gap spread inside words falls from 6.1 to 2.3 for lowercase words and from 7.2 to 2.5 for capitalised words and those letters. This is a measure of the model, not of perception; the moderate 0.7 share is deliberate. A first version with 20-unit buckets added noise (6.0 to 8.1), which is why the buckets are fine.

Two exceptions are added for `f` and `t`. First, their crossbars: the model reads the bar as filling the room on the left of the stem, but a bar is a seventh of the height, so the stem of `t` looked detached from the letter before it (stem to stem 199 units in `at` against 154 in `an`). The left bearing of `t` and `f` gets 25 extra in the kerning model, which brings `at`, `ht`, `nt` to about 190. Second, the four pairs `ff`, `ft`, `tf` and `tt` get explicit glyph-pair kerning that puts the bar ends 0.85 stem widths apart (65 units Regular, 100 Bold, about one bar thickness). Without it the gap was 38 to 52 (uneven, a hairline at display sizes); joining the bars was tried and tightened the pair too much, and 95 units looked airy.

## 8. Monospace

- **Grid:** 550-unit cell, every one of the 3,084 codepoints exactly one cell wide, and `isFixedPitch` set. Iosevka's `term` spacing is what guarantees em dash, arrows and ellipsis fit one cell. The earlier "normal" mono spacing made 470 glyphs two cells wide.
- **Width choice:** reduced from 580 to 550 after feedback that there was too much horizontal space.
- **Anchored `i`, `l`, `j`:** compared against Commit Mono on the owner's machine, whose `l` and `i` span about 70 percent of the cell (a top flag or serif and a foot) while ours were bare 76 to 120 unit sticks that floated (optical bearing 237 units a side against about 85 for round letters). The mono first used `i` serifed, `l` tailed-serifed and `j` serifed, which brought `i` to about 155 and gave `l` a foot, but left `l` about 20 percent wider than `i` (respected monospaces stay within about 8 percent) and `j` as wide as `i` (they sit near 70 percent). It then used `l` serifed-flat-tailed and `j` narrow-serifed (`l` 1.03, `j` 0.82 of `i`'s ink width) and now `j` flat-hook-serifed, whose hook is cut to the length of `l`'s tail: `l` is 1.03 and `j` 0.67 of `i`'s ink width. Chosen by rendering four combinations (serifed or tailed `i`, serifed, tailed-serifed or flat-tailed `l`) and comparing words such as "illusion little fill hijack lilliput". Outlines come from Iosevka's own variants, not from Commit Mono.
- **`W`, `w`, `M`, `m`:** four strokes in one cell leave slivers that shimmer in rows of `WWWW` at small sizes. A flat-top `W` and `w` (lower middle apex) plus a closing radius of 22 gives solid feet and open counters. A radius of 32 was too heavy.
- **Tucking (`tuck.py`):** narrow letters leave more air than their neighbours. Every glyph keeps its advance; contextual `kern` positioning shifts glyphs inside their own cells.
  - Eligible glyphs: letters and `. , : ; ! ?`. Digits, brackets and operators stay centred so columns and code keep their rhythm.
  - Each glyph gets an *optical bearing* per side (sidebearing plus 0.6 x depth). The optical gap of a pair is the first glyph's right bearing plus the second's left bearing. The target is the median gap over all pairs minus 30 (177 in the Regular). The median alone was too loose a target: round-letter pairs sit near 165, so `bo` and `oo` counted as already fine while `ol` (300) was tucked, which left `bool` with tight `bo`, loose `oo`.
  - A letter pair whose gap exceeds the target is closed by `0.6 x (gap - target)`, at most 120 units, and the closure is shared over four glyphs: the pair's two glyphs take half each (the first moves right, the second left) and the glyph before the pair and the glyph after it take a quarter each, in the same direction. Offsets are rounded down to 5 units and nothing happens below a closure of 20. Sharing is the point: when only the pair moved, the air taken from a loose pair landed on one neighbouring gap (`bool` first became `bo` 165, `oo` 207, `ol` 220). With the quarter shares it lands over two gaps on each side (`bo` 185, `oo` 187, `ol` 220). Rules are generated per bucket pair (24-unit buckets), about 350 in all. Buckets of 20 gave marginally better numbers but pushed the Regular's table past the 64 KB offset limit, which made the compiler switch to extension lookups and grew the font by 300 to 450 KB; buckets of 30 to 40 give up 5 to 10 percent of the gain.
  - A pair of a letter and a sentence mark moves only the mark, by the whole shift `0.8 x (gap - target)` capped at 140. The mark owns the air in its own cell; the first version split the shift, which dragged the letter before a colon away from the rest of its word (`sources:` moved `s` 65 units toward the colon, `(claim:` moved `m` toward it and `c` away from the bracket).
  - A letter never moves away from a neighbour that does not take part (ASCII punctuation, brackets, digits, Latin-1 punctuation, general punctuation). This is an `ignore pos` rule ahead of each shifting rule, so `(c` keeps its gap. A mark followed by such a glyph, as in `claim:)`, stays put for the same reason.
  - Four chained lookups do it, one per role of a glyph in a loose pair (first, second, the glyph before, the glyph after), and a glyph's offsets add up when it has several roles. The glyph-before and glyph-after roles apply to ASCII and Latin-1 letters only; a larger class made the table 8 times bigger for no visible gain.
  - This replaces the base's mark and mkmk positioning; the character set contains only precomposed characters, so nothing depends on it.
  - It uses positioning, not glyph substitution. Fonts such as Commit Mono ("smart kerning") and Monaspace ("texture healing") do the equivalent with contextual alternates through `calt`, which also works where kerning is ignored but needs hundreds of shifted glyph variants. Positioning is smaller and simpler and is what browsers apply by default.
  - Measured with the real shaper (HarfBuzz) over 4,000 random dictionary words of 5 to 12 letters: the standard deviation of the optical gaps inside a word falls from 46.1 untucked to 25.9, the mean absolute difference between adjacent gaps from 46.7 to 21.5, the mean largest gap from 299 to 253 and the mean smallest rises from 161 to 176, so nothing crowds: the smallest ink clearance between neighbouring letters is 58 units. Letters drift a mean 39 units at most per word (worst 90, about a sixth of a cell). Over the prose of this repository: letter-to-mark gaps average 337 untucked and 258 tucked, and gaps next to brackets, digits and quotes are unchanged (the first version loosened them by about 8 units on average and up to 65). `bool:` shows offsets `0, 20, 40, -40, -140` and `verify:` `5, 25, 40, 20, -25, -50, -140`, all advances 550.
- **Drawing glyphs** are exactly the base's geometry. Box glyphs span 1200 units vertically, equal to the line box, so vertical lines tile between rows.

## 9. Build system

- Python 3.10 or newer, managed with **uv** (`pyproject.toml`, `uv.lock`). Dependencies: `fonttools` and `skia-pathops` only. Node and npm are needed to build Iosevka; `git` to fetch it.
- **`make`** builds everything and is incremental: the Iosevka base (stamp `build/base/.built`) rebuilds only when `font/iosevka-plan.toml` or `font/iosevka.py` changes; each font rebuilds when the base or any script in `font/` changes; the specimen and licence are copies. `make -j2` builds in parallel; `make clean` removes `dist/`; `make distclean` also removes `build/` and `.venv`.
- Builds are reproducible: font timestamps are fixed (`SOURCE_DATE_EPOCH`, or a constant release date), so a fresh build is byte-identical to the committed `dist/` and a clean `git status` after `make` means the fonts are current.
- `build/` (Iosevka checkout, base fonts, scratch files) and `.venv/` are not committed.
- Per-font entry point: `uv run font/build.py BASE.ttf OUT.ttf --weight Regular|Bold [--mono]`.
- Tuning constants live at the top of `font/build.py` (`TARGET_STEM`, `STYLE`, `SPACING`, `CLOSE_RADIUS`, `MONO_FILL`) and in `font/tuck.py` and `font/charset.py`.

## 10. Verification performed

- All four TTFs load in Chrome (`document.fonts` reports `loaded`), including from `file://`. A browser sanitizer failure caught here (the overlap bits above) is why `finish()` clears flags.
- Refactors were checked by diffing outlines and metrics against the earlier build: zero differences, in both uv and the previous environment.
- The bracket fix changed only Ps and Pe glyphs (8 or 9 per font) and no advances.
- Monospace: every advance is 550, `isFixedPitch` is set, box-drawing glyphs match the base outlines, and a rendered box, rounded corners, double lines, blocks and Braille line up.
- Tucking: confirmed with a text shaper (HarfBuzz) that offsets change and advances do not.
- The specimen was rendered at body and display sizes for both families.
- Harmony audit (optical bearing per letter against the median): sans `j` 295 to 136 on the left; mono `i` 237 to about 155, `l` anchored. Remaining sans outliers (`T f L F Y E J`) are handled by kerning; mono outliers by anchoring and tucking.
- Against the previous build the mono changed only `i`, `j`, `l` and their accented forms, with no advance changes. The sans changed `j`, `l`, and `A J T V X Y Z f t`, because the left clearance for ink inside the zone went from 24 to the floor of 14 when hooks were allowed to overhang.
- Two from-scratch builds of all four fonts are byte-identical, and every font loads in Chrome.

## 11. Known limitations and open items

- **Tucking still moves air, it does not remove it.** Cells are fixed, so tightening a loose pair loosens neighbouring gaps; the shared closure spreads that over two gaps a side. About 5 percent of letter-pair gaps in prose still widen by more than 30 units (up to 75), mostly tight gaps moving toward the target, and about 24 percent of the few mark-then-letter pairs (`e.g`, `file.txt`) loosen because the mark hugs the letter before it. Offsets reach 90 units in the worst words.
- **Not tested** in the artifact viewer, in editors, or in terminals. Applications that ignore `kern` show the monospace without tucking (still correct, just plain cells).
- Tucking redistributes space inside a word rather than adding ink: a narrow letter is still narrow. At 15 px the shifts are about one pixel; the effect is clearer at larger sizes. Stronger settings gave small further gains.
- **Iosevka is not pinned.** `iosevka.py` clones the default branch, so a later Iosevka release could change outlines. The fix is to pin a tag and re-verify.
- Italics are browser-synthesized. A true oblique could come from Iosevka's slope settings through the same pipeline, but that is not built.
- The `W` fix is a fill, so rows of `WWWW` are heavier at the base than the rest of the glyphs.
- Greek letters that are math symbols (Δ π μ) are not covered, by decision.
- Open: whether to pin the Iosevka version; whether to add a true oblique. Kerning strength (0.7) and the tucking limits were chosen from a model and a few renders, not from reading tests.

## 12. Licence and attribution

Derivative of [Iosevka](https://github.com/be5invis/Iosevka) (Copyright 2015 to 2026 Renzhi Li), SIL Open Font License 1.1 (`OFL.txt`). The fonts and the build scripts stay under the OFL. The fonts are renamed to Stochastic Sans and Stochastic Mono.
