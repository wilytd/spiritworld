"""
LLM Service with provider fallback orchestration
"""

import json
import logging
from typing import Optional, Dict, Any, List

from .config import LLMConfig
from .base import BaseLLMProvider, LLMResponse
from .providers import OllamaProvider, OpenAIProvider, AnthropicProvider
from . import prompts

logger = logging.getLogger(__name__)


class LLMService:
    """
    Orchestrates LLM providers with automatic fallback.
    Tries providers in configured priority order.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._availability: Dict[str, bool] = {}

        # Initialize providers
        self._init_providers()

    def _init_providers(self):
        """Initialize all configured providers"""
        if self.config.ollama.is_configured:
            self._providers["ollama"] = OllamaProvider(self.config.ollama)

        if self.config.openai.is_configured:
            self._providers["openai"] = OpenAIProvider(self.config.openai)

        if self.config.anthropic.is_configured:
            self._providers["anthropic"] = AnthropicProvider(self.config.anthropic)

    async def check_availability(self) -> Dict[str, bool]:
        """Check availability of all providers"""
        self._availability.clear()

        for name, provider in self._providers.items():
            try:
                available = await provider.is_available()
                self._availability[name] = available
                logger.info(f"Provider {name}: {'available' if available else 'unavailable'}")
            except Exception as e:
                logger.error(f"Error checking {name} availability: {e}")
                self._availability[name] = False

        return dict(self._availability)

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "enabled": self.config.enabled,
            "providers": {
                name: {
                    **provider.get_status(),
                    "available": self._availability.get(name),
                }
                for name, provider in self._providers.items()
            },
            "priority": self.config.provider_priority,
            "analysis_enabled": self.config.enable_analysis,
            "analysis_schedule": self.config.analysis_schedule,
        }

    async def _get_available_provider(
        self,
        exclude: Optional[set] = None
    ) -> Optional[BaseLLMProvider]:
        """
        Get first available provider in priority order.

        Args:
            exclude: Set of provider names to skip (already attempted this request)
        """
        exclude = exclude or set()

        for provider_name in self.config.provider_priority:
            if provider_name not in self._providers:
                continue

            if provider_name in exclude:
                continue

            provider = self._providers[provider_name]

            # Check cached availability first
            if self._availability.get(provider_name) is False:
                continue

            # Verify availability if not cached
            if provider_name not in self._availability:
                try:
                    self._availability[provider_name] = await provider.is_available()
                except Exception:
                    self._availability[provider_name] = False

            if self._availability.get(provider_name):
                return provider

        return None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Optional[LLMResponse]:
        """
        Generate completion using first available provider.
        Automatically falls back to next provider on failure.
        Returns None if no providers are available.
        """
        if not self.config.enabled:
            logger.warning("LLM service is disabled")
            return None

        attempted: set = set()

        while True:
            provider = await self._get_available_provider(exclude=attempted)
            if not provider:
                if attempted:
                    logger.error(f"All LLM providers failed. Attempted: {attempted}")
                else:
                    logger.error("No LLM providers available")
                return None

            attempted.add(provider.name)

            try:
                response = await provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.debug(f"Completion from {provider.name}: {len(response.content)} chars")
                return response
            except Exception as e:
                logger.error(f"Error from {provider.name}: {e}")
                # Mark as unavailable for future requests
                self._availability[provider.name] = False
                # Loop continues to try next provider

    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate JSON completion and parse result.
        Automatically falls back to next provider on failure.
        Returns None if no providers available or parsing fails.
        """
        if not self.config.enabled:
            return None

        attempted: set = set()

        while True:
            provider = await self._get_available_provider(exclude=attempted)
            if not provider:
                if attempted:
                    logger.error(f"All LLM providers failed. Attempted: {attempted}")
                else:
                    logger.error("No LLM providers available")
                return None

            attempted.add(provider.name)

            try:
                response = await provider.complete_json(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Parse JSON response
                try:
                    parsed = json.loads(response.content)
                    return {
                        "data": parsed,
                        "provider": response.provider,
                        "model": response.model,
                        "usage": response.usage,
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from {provider.name}: {e}")
                    logger.debug(f"Raw response: {response.content[:500]}")
                    # Don't fallback for JSON parse errors - that's a response quality issue
                    return None

            except Exception as e:
                logger.error(f"Error from {provider.name}: {e}")
                # Mark as unavailable for future requests
                self._availability[provider.name] = False
                # Loop continues to try next provider

    async def analyze_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze a single task and provide recommendations.

        Args:
            task: Dict with title, description, category, priority, due_date, status

        Returns:
            Analysis result with suggested_priority, reasoning, etc.
        """
        prompt = prompts.SINGLE_TASK_ANALYSIS_PROMPT.format(
            title=task.get("title", ""),
            description=task.get("description", ""),
            category=task.get("category", ""),
            priority=task.get("priority", ""),
            due_date=task.get("due_date", "Not set"),
            status=task.get("status", ""),
        )

        result = await self.complete_json(
            prompt=prompt,
            system_prompt=prompts.TASK_ANALYSIS_SYSTEM,
        )

        if result:
            result["task_id"] = task.get("id")
            result["analysis_type"] = "single"

        return result

    async def analyze_tasks_batch(self, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyze a batch of tasks and provide prioritization.

        Args:
            tasks: List of task dicts

        Returns:
            Analysis with priority_order, urgent_tasks, groupings, etc.
        """
        # Simplify tasks for prompt
        simplified = [
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "description": t.get("description", "")[:200],
                "category": t.get("category"),
                "priority": t.get("priority"),
                "due_date": str(t.get("due_date")) if t.get("due_date") else None,
            }
            for t in tasks
        ]

        prompt = prompts.BATCH_ANALYSIS_PROMPT.format(
            tasks_json=json.dumps(simplified, indent=2)
        )

        result = await self.complete_json(
            prompt=prompt,
            system_prompt=prompts.BATCH_ANALYSIS_SYSTEM,
        )

        if result:
            result["analysis_type"] = "batch"
            result["task_count"] = len(tasks)

        return result


# Global service instance (initialized from config)
llm_service: Optional[LLMService] = None


def init_llm_service(config: Optional[LLMConfig] = None) -> LLMService:
    """Initialize the global LLM service"""
    global llm_service
    if config is None:
        config = LLMConfig.from_env()
    llm_service = LLMService(config)
    return llm_service


def get_llm_service() -> Optional[LLMService]:
    """Get the global LLM service instance"""
    return llm_service
