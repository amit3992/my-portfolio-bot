.PHONY: install lint test run clean build setup

# Python virtual environment
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Project settings
PORT = 8000

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pylint pytest pytest-cov black

lint:
	$(PYTHON) -m pylint app.py rag_engine.py llm_router.py load_resume.py
	$(PYTHON) -m black --check .

format:
	$(PYTHON) -m black .

test:
	$(PYTHON) -m pytest tests/ --cov=. --cov-report=term-missing

run:
	$(PYTHON) -m uvicorn app:app --reload --port $(PORT)

setup:
	$(PYTHON) -c "from rag_engine import load_resume_embeddings; load_resume_embeddings()"

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf embeddings/
	find . -type d -name "__pycache__" -exec rm -r {} +

build: clean install setup
