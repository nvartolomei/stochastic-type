UV ?= uv
WEIGHTS := Regular Bold

# Iosevka base: built from source (needs git, node, npm); rebuilt only when its plan changes.
BASE_STAMP := build/base/.built
FONTS := $(foreach w,$(WEIGHTS),dist/StochasticSans-$(w).ttf dist/StochasticMono-$(w).ttf)
WOFF2 := $(FONTS:.ttf=.woff2)
SCRIPTS := $(wildcard font/*.py)

.PHONY: all shots clean distclean

all: $(FONTS) $(WOFF2) dist/specimen.html dist/OFL.txt

$(BASE_STAMP): font/iosevka-plan.toml font/iosevka.py
	$(UV) run font/iosevka.py
	touch $@

dist/StochasticSans-%.ttf: $(BASE_STAMP) $(SCRIPTS)
	@mkdir -p dist
	$(UV) run font/build.py build/base/IosevkaStochastic-$*.ttf $@ --weight $*

dist/StochasticMono-%.ttf: $(BASE_STAMP) $(SCRIPTS)
	@mkdir -p dist
	$(UV) run font/build.py build/base/IosevkaStochasticMono-$*.ttf $@ --weight $* --mono

dist/%.woff2: dist/%.ttf font/woff2.py
	$(UV) run font/woff2.py $< $@

# Static page; it loads the fonts from the same directory.
dist/specimen.html: specimen/index.html
	@mkdir -p dist
	cp $< $@

dist/OFL.txt: OFL.txt
	@mkdir -p dist
	cp $< $@

# README screenshots, rendered at 2x with headless Chrome.
shots: $(FONTS)
	$(UV) run specimen/shots.py

clean:
	rm -rf dist

distclean: clean
	rm -rf build .venv
