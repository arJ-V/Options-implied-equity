.PHONY: install data signals backtest dashboard test clean

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

data:
	./scripts/download_release.sh

signals:
	$(PYTHON) run_signals.py --start 2020-01-01 --end 2024-12-31

backtest:
	$(PYTHON) run_backtest.py --horizon 21

dashboard:
	$(PYTHON) -m streamlit run app/dashboard.py

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
