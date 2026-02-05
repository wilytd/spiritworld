"""
LLM configuration settings
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OllamaConfig:
    """Configuration for Ollama (local LLM)"""
    url: str = "http://localhost:11434"
    model: str = "llama3.2"
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        return cls(
            url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "120.0")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.url)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI"""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    timeout: float = 60.0
    max_tokens: int = 2048

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            timeout=float(os.getenv("OPENAI_TIMEOUT", "60.0")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2048")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic"""
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    timeout: float = 60.0
    max_tokens: int = 2048

    @classmethod
    def from_env(cls) -> "AnthropicConfig":
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            timeout=float(os.getenv("ANTHROPIC_TIMEOUT", "60.0")),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class LLMConfig:
    """Main LLM configuration"""
    enabled: bool = True
    provider_priority: List[str] = field(default_factory=lambda: ["ollama", "openai", "anthropic"])
    enable_analysis: bool = True
    analysis_schedule: str = "0 6 * * *"  # Default: 6 AM daily

    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        priority_str = os.getenv("LLM_PROVIDER_PRIORITY", "ollama,openai,anthropic")
        priority = [p.strip() for p in priority_str.split(",") if p.strip()]

        return cls(
            enabled=os.getenv("LLM_ENABLED", "true").lower() == "true",
            provider_priority=priority,
            enable_analysis=os.getenv("LLM_ENABLE_ANALYSIS", "true").lower() == "true",
            analysis_schedule=os.getenv("LLM_ANALYSIS_SCHEDULE", "0 6 * * *"),
            ollama=OllamaConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            anthropic=AnthropicConfig.from_env(),
        )

    def get_provider_config(self, provider_name: str):
        """Get config for a specific provider"""
        configs = {
            "ollama": self.ollama,
            "openai": self.openai,
            "anthropic": self.anthropic,
        }
        return configs.get(provider_name)

    @property
    def has_any_provider(self) -> bool:
        """Check if any provider is configured"""
        return (
            self.ollama.is_configured or
            self.openai.is_configured or
            self.anthropic.is_configured
        )
