UV ?= uv
WEIGHTS := Regular Bold

# Iosevka base: built from source (needs git, node, npm); rebuilt only when its plan changes.
BASE_STAMP := build/base/.built
FONTS := $(foreach w,$(WEIGHTS),dist/StochasticSans-$(w).ttf dist/StochasticMono-$(w).ttf)
SCRIPTS := $(wildcard font/*.py)

.PHONY: all clean distclean

all: $(FONTS) dist/specimen.html dist/OFL.txt

$(BASE_STAMP): font/iosevka-plan.toml font/iosevka.py
	$(UV) run font/iosevka.py
	touch $@

dist/StochasticSans-%.ttf: $(BASE_STAMP) $(SCRIPTS)
	@mkdir -p dist
	$(UV) run font/build.py build/base/IosevkaStochastic-$*.ttf $@ --weight $*

dist/StochasticMono-%.ttf: $(BASE_STAMP) $(SCRIPTS)
	@mkdir -p dist
	$(UV) run font/build.py build/base/IosevkaStochasticMono-$*.ttf $@ --weight $* --mono

# Static page; it loads the fonts from the same directory.
dist/specimen.html: specimen/index.html
	@mkdir -p dist
	cp $< $@

dist/OFL.txt: OFL.txt
	@mkdir -p dist
	cp $< $@

clean:
	rm -rf dist

distclean: clean
	rm -rf build .venv
