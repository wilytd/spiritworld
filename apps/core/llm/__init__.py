"""
Aegis Mesh LLM Integration

Multi-provider LLM integration with:
- Ollama (local, priority)
- OpenAI
- Anthropic

Provides automatic fallback between providers.
"""

from .config import LLMConfig, OllamaConfig, OpenAIConfig, AnthropicConfig
from .base import BaseLLMProvider, LLMResponse
from .service import LLMService, llm_service

__all__ = [
    "LLMConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "AnthropicConfig",
    "BaseLLMProvider",
    "LLMResponse",
    "LLMService",
    "llm_service",
]
