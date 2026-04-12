#!/bin/bash
# Start Ollama server in background, wait for it, then pull the embedding model

# Start Ollama server
ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama server to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama server is ready!"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done

# Pull the embedding model if not already present
echo "Ensuring nomic-embed-text model is available..."
ollama pull nomic-embed-text

echo "Ollama is ready with nomic-embed-text model."

# Keep the server running in foreground
wait
