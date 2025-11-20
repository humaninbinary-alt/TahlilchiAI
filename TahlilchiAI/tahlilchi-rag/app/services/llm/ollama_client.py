"""Ollama LLM API client."""

import json
import logging
from typing import AsyncGenerator, Optional

import httpx

from app.config import settings
from app.core.exceptions import LLMConnectionError, LLMGenerationError, LLMTimeoutError

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for Ollama LLM API.

    Handles:
    - API communication
    - Error handling
    - Timeout management
    - Response parsing
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.LLM_TIMEOUT,
    ) -> None:
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama API base URL
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.logger = logger

    async def generate(
        self,
        prompt: str,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate text completion from Ollama.

        Args:
            prompt: User prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Max tokens to generate
            system_prompt: Optional system prompt

        Returns:
            Generated text

        Raises:
            LLMConnectionError: If cannot connect to Ollama
            LLMTimeoutError: If request times out
            LLMGenerationError: If generation fails
        """
        try:
            self.logger.info(f"Generating with Ollama model: {self.model}")

            # Build full prompt with system message if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stream": False,
                    },
                )

                response.raise_for_status()
                result = response.json()

                # Extract generated text
                generated_text = result.get("response", "")

                if not generated_text:
                    raise LLMGenerationError("Empty response from Ollama")

                self.logger.info(f"Generated {len(generated_text)} characters")
                return generated_text.strip()

        except httpx.TimeoutException as e:
            self.logger.error(f"Ollama request timeout: {e}")
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s")

        except httpx.ConnectError as e:
            self.logger.error(f"Cannot connect to Ollama: {e}")
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. " "Is Ollama running?"
            )

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            raise LLMGenerationError(f"Ollama API error: {e.response.status_code}")

        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise LLMGenerationError(f"Generation failed: {e}")

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate text completion with streaming from Ollama.

        Yields tokens as they are generated in real-time.

        Args:
            prompt: User prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Max tokens to generate
            system_prompt: Optional system prompt

        Yields:
            Generated tokens one by one

        Raises:
            LLMConnectionError: If cannot connect to Ollama
            LLMTimeoutError: If request times out
            LLMGenerationError: If generation fails
        """
        try:
            self.logger.info(f"Streaming with Ollama model: {self.model}")

            # Build full prompt with system message if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Make streaming API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    # Parse streaming response line by line
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            # Each line is a JSON object
                            chunk = json.loads(line)
                            token = chunk.get("response", "")

                            if token:
                                yield token

                            # Check if done
                            if chunk.get("done", False):
                                self.logger.info("Streaming completed")
                                break

                        except json.JSONDecodeError:
                            self.logger.warning(f"Failed to parse chunk: {line}")
                            continue

        except httpx.TimeoutException as e:
            self.logger.error(f"Ollama streaming timeout: {e}")
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s")

        except httpx.ConnectError as e:
            self.logger.error(f"Cannot connect to Ollama: {e}")
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?"
            )

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            raise LLMGenerationError(f"Ollama API error: {e.response.status_code}")

        except Exception as e:
            self.logger.error(f"Ollama streaming failed: {e}")
            raise LLMGenerationError(f"Streaming failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if Ollama is running and model is available.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()

                # Check if our model is available
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                if self.model in models:
                    self.logger.info(f"Ollama healthy, model {self.model} available")
                    return True
                else:
                    self.logger.warning(f"Model {self.model} not found in Ollama")
                    return False

        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False
