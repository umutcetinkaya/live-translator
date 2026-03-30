VERSION ?= 0.0.1

.PHONY: install run build dmg models clean

install:
	@echo "=== Installing Live Translator ==="
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -q
	@echo "=== Done! Run: make run ==="

run:
	@.venv/bin/python main.py

models:
	@bash scripts/download_models.sh

build:
	@bash scripts/build_app.sh $(VERSION)

dmg: build
	@bash scripts/build_dmg.sh $(VERSION)

clean:
	rm -rf build dist
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
