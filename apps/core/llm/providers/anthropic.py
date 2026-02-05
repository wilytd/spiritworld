"""
Anthropic LLM provider
"""

import logging
from typing import Optional, Dict, Any

from ..base import BaseLLMProvider, LLMResponse
from ..config import AnthropicConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider"""

    def __init__(self, config: AnthropicConfig):
        self.config = config
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                logger.error("anthropic package not installed")
                raise
        return self._client

    async def is_available(self) -> bool:
        """Check if Anthropic API is accessible"""
        if not self.is_configured:
            return False

        try:
            # Anthropic doesn't have a lightweight health check,
            # so we just verify the client can be created
            self._get_client()
            return True
        except Exception as e:
            logger.debug(f"Anthropic not available: {e}")
            return False

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate completion using Anthropic"""
        client = self._get_client()

        kwargs: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await client.messages.create(**kwargs)

        content = ""
        if response.content:
            content = response.content[0].text

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
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
        """
        Generate JSON completion using Anthropic.
        Anthropic doesn't have native JSON mode, so we add instruction.
        """
        json_system = (system_prompt or "") + "\n\nYou must respond with valid JSON only. No markdown code blocks, no explanation, just the JSON object."

        return await self.complete(
            prompt=prompt,
            system_prompt=json_system.strip(),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.is_configured,
            "model": self.config.model,
        }
