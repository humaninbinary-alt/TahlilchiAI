.PHONY: help install test format lint clean security run jupyter

help:
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make test       - Run tests with coverage"
	@echo "  make format     - Format code with black and ruff"
	@echo "  make lint       - Run all linters"
	@echo "  make clean      - Remove build artifacts"
	@echo "  make security   - Run security checks"
	@echo "  make jupyter    - Start Jupyter notebook server"
	@echo "  make freeze     - Generate requirements.txt"

install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v --cov=src --cov-report=term-missing --cov-report=html

format:
	black src tests
	ruff check --fix src tests
	isort src tests

lint:
	black --check src tests
	ruff check src tests
	mypy src
	pylint src
	flake8 src tests

security:
	bandit -r src
	safety check

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf build dist

jupyter:
	jupyter notebook --notebook-dir=notebooks

freeze:
	pip freeze > requirements.txt
