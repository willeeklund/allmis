PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python
PORT ?= 1010

.PHONY: dev install fetch test serve clean

dev: fetch serve

install: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt
	touch $@

fetch: install
	$(PY) -m allmis.fetch

test: install
	$(PY) -m pytest -q

serve:
	@echo "Öppna http://localhost:$(PORT)"
	$(PYTHON) -m http.server $(PORT) --directory docs

clean:
	rm -rf $(VENV) .pytest_cache
