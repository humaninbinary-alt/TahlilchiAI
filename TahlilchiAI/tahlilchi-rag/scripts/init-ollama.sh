#!/bin/bash
# Initialize Ollama with required models

set -e

echo "Waiting for Ollama to be ready..."
until curl -f http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "Ollama is unavailable - sleeping"
    sleep 5
done

echo "Ollama is ready!"

echo "Pulling qwen2.5:7b model..."
ollama pull qwen2.5:7b

echo "Model pulled successfully!"
echo "Available models:"
ollama list
