SHELL := /bin/bash -euxo pipefail

.PHONY: docs
docs:
	uv run --extra=dev sphinx-build -M html docs/source docs/build -W

.PHONY: open-docs
open-docs:
	python -c 'import os, webbrowser; webbrowser.open("file://" + os.path.abspath("docs/build/html/index.html"))'
