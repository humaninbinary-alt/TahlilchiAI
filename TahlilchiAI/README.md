# TahlilchiAI

An AI/ML project for intelligent analysis.

## Features

- Modern Python development setup with best practices
- Comprehensive code quality tools (Black, Ruff, MyPy, Pylint)
- Pre-commit hooks for automated code quality checks
- AI/ML libraries: PyTorch, Transformers, scikit-learn
- LLM integration: OpenAI, Anthropic, LangChain
- Testing framework with pytest
- Security scanning with Bandit and Safety

## Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd TahlilchiAI
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Project Structure

```
TahlilchiAI/
├── src/
│   └── tahlilchi/
│       ├── __init__.py
│       ├── models/
│       ├── data/
│       ├── utils/
│       └── config/
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── notebooks/
│   └── exploratory/
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── configs/
├── scripts/
├── docs/
├── .pre-commit-config.yaml
├── pyproject.toml
├── .gitignore
├── .env.example
├── Makefile
└── README.md
```

## Development

### Running Tests

```bash
make test
```

### Code Quality

Run all code quality checks:
```bash
make lint
```

Format code:
```bash
make format
```

### Common Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make test          # Run tests
make format        # Format code
make lint          # Run linters
make clean         # Clean build artifacts
make security      # Run security checks
```

## Usage

```python
# Example usage will go here
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Submit a pull request

## License

MIT License
