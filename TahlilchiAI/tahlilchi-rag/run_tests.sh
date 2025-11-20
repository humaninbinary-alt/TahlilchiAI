#!/bin/bash
# Test runner script with various options

set -e

echo "TahlilchiAI RAG System - Test Runner"
echo "===================================="

# Parse command line arguments
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        echo "Running unit tests..."
        pytest tests/unit -v -m unit
        ;;
    integration)
        echo "Running integration tests..."
        pytest tests/integration -v -m integration
        ;;
    api)
        echo "Running API tests..."
        pytest tests/api -v
        ;;
    coverage)
        echo "Running tests with coverage..."
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo "Coverage report generated in htmlcov/index.html"
        ;;
    fast)
        echo "Running fast tests only..."
        pytest -v -m "unit and not slow"
        ;;
    parallel)
        echo "Running tests in parallel..."
        pytest -n auto -v
        ;;
    all)
        echo "Running all tests..."
        pytest -v
        ;;
    *)
        echo "Usage: $0 {unit|integration|api|coverage|fast|parallel|all}"
        exit 1
        ;;
esac

echo ""
echo "Tests completed!"
