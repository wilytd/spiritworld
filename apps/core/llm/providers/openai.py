"""
OpenAI LLM provider
"""

import logging
from typing import Optional, Dict, Any

from ..base import BaseLLMProvider, LLMResponse
from ..config import OpenAIConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""

    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                logger.error("openai package not installed")
                raise
        return self._client

    async def is_available(self) -> bool:
        """Check if OpenAI API is accessible"""
        if not self.is_configured:
            return False

        try:
            client = self._get_client()
            # Quick model list check
            await client.models.retrieve(self.config.model)
            return True
        except Exception as e:
            logger.debug(f"OpenAI not available: {e}")
            return False

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI"""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )

        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate JSON completion using OpenAI's JSON mode"""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.is_configured,
            "model": self.config.model,
        }
