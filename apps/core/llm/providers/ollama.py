"""
Ollama LLM provider for local inference
"""

import logging
from typing import Optional, Dict, Any

import httpx

from ..base import BaseLLMProvider, LLMResponse
from ..config import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider for local LLM inference.
    Prioritized for privacy and offline operation.
    """

    def __init__(self, config: OllamaConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.url,
                timeout=self.config.timeout,
            )
        return self._client

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        if not self.is_configured:
            return False

        try:
            client = await self._get_client()
            # Check if server is up
            response = await client.get("/api/tags")
            if response.status_code != 200:
                return False

            # Check if model exists
            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            model_name = self.config.model.split(":")[0]

            if model_name not in models:
                logger.debug(f"Ollama model {self.config.model} not found. Available: {models}")
                return False

            return True

        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate completion using Ollama"""
        client = await self._get_client()

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()

        data = response.json()

        return LLMResponse(
            content=data.get("response", ""),
            provider=self.name,
            model=self.config.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )

    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate JSON completion using Ollama's format parameter"""
        client = await self._get_client()

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()

        data = response.json()

        return LLMResponse(
            content=data.get("response", ""),
            provider=self.name,
            model=self.config.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.is_configured,
            "url": self.config.url,
            "model": self.config.model,
        }
