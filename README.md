# Stochastic Type

Stochastic Type is a font family for LLM-published content, built by a stochastic parrot. Made for long prose: letters are spaced from their outlines, weights are moderate, and bowls are squircles rather than circles or boxes.

It is a derivative of [Iosevka](https://github.com/be5invis/Iosevka) (SIL OFL 1.1, `OFL.txt`) and stays OFL. Two typefaces, Stochastic Sans (proportional) and Stochastic Mono (fixed cell, every glyph one cell wide), each static Regular and Bold. Latin (including Vietnamese), punctuation, currency, arrows, math, shapes and common symbols, plus box drawing, block elements, Braille, Powerline and legacy-computing graphics. No other scripts.

## Build

```
make
```

Managed with [uv](https://docs.astral.sh/uv/): every step runs through `uv run`, which creates the environment from `pyproject.toml` and `uv.lock` on first use. The Iosevka base is built from source, so `git`, `node` and `npm` are also needed. The first `make` clones Iosevka into `build/` and takes a few minutes; after that the graph is incremental: changing a script in `font/` rebuilds the fonts, and the Iosevka base is rebuilt only when `font/iosevka-plan.toml` or `font/iosevka.py` changes. `make -j2` builds both weights in parallel. `make clean` removes `dist/`; `make distclean` also removes `build/` and `.venv`.

Outputs in `dist/`: `StochasticSans-{Regular,Bold}.ttf`, `StochasticMono-{Regular,Bold}.ttf`, `OFL.txt`, and `specimen.html`, a static page that loads the fonts from the same directory (open it straight from disk). Static fonts only, TTF only.

## Pipeline

| Step | File | What it does |
|---|---|---|
| Base | `iosevka-plan.toml`, `iosevka.py` | Two custom Iosevka builds, quasi-proportional sans and `term` monospace, double-storey `a`, single-storey `g`, straight `y`, slashed zero, serifed `I`; semi-tailed `l`, narrow `j` and compact `r` in the sans, anchored (serifed) `i`, flat-tailed `l` and narrow `j` in the mono; x-height and cap height set through `metricOverride`. |
| Subset and scale | `build.py`, `charset.py` | Keeps the codepoints in `charset.py` (Latin and symbols, no other scripts), scales to the target x-height. |
| Spacing | `spacing.py`, `kerning.py`, `tuck.py` | Sans: Iosevka centres letters in near-uniform cells; `kerning.py` then adds pair kerning that moves every pair toward one optical gap. Sidebearings are recomputed from each outline: straight sides get room, receding sides (`t f r v y`) less, digits stay tabular, hooks keep clearance, accents follow their base. Mono: the fixed cell stays, and `tuck.py` adds contextual `kern` positioning that nudges narrow letters toward their neighbours inside their own cells (advances never change). |
| Restyle | `restyle.py`, `squarify.py`, `outline.py` | Stems moved to the target weight, curved runs pushed toward squircles along their normals (`squircle_n`, 3.2 here), thin slivers closed, near-vertical and near-horizontal strokes snapped to the axes. Composite glyphs are untouched so accents and kerning keep working. Box drawing, block elements, Braille, legacy-computing and Powerline glyphs are left exactly as the base drew them so lines meet across cells. |

Tuning knobs live at the top of `font/build.py`: `TARGET_STEM`, `STYLE` (squircle push), `SPACING` (`target`, `strength`), `CLOSE_RADIUS`.
