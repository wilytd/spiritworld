"""
Base LLM provider abstract class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class LLMResponse:
    """Response from an LLM provider"""
    content: str
    provider: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)  # tokens used
    raw_response: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider must implement:
    - name property: Provider identifier
    - is_available(): Check if provider can be used
    - complete(): Generate a completion
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier"""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider has required configuration"""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available (API reachable, model exists, etc.)
        Should be a quick health check.
        """
        ...

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with the generated content
        """
        ...

    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a JSON completion.
        Default implementation adds JSON instruction to prompt.
        Override for providers with native JSON mode.
        """
        json_instruction = "\n\nRespond with valid JSON only. No markdown, no explanation."
        return await self.complete(
            prompt=prompt + json_instruction,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get provider status information"""
        return {
            "name": self.name,
            "configured": self.is_configured,
        }
