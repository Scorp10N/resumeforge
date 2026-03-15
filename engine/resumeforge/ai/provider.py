"""AI provider — LiteLLM wrapper with non-AI fallbacks."""

from __future__ import annotations

import logging

from resumeforge.data.schema import AIConfig

logger = logging.getLogger(__name__)

# Message dict type for LiteLLM
_Message = dict[str, str]


class AIProvider:
    """Thin wrapper around LiteLLM. Falls back gracefully when AI is disabled."""

    def __init__(self, config: AIConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def complete(
        self,
        prompt: str,
        system: str = "You are a professional resume writing assistant.",
        temperature: float | None = None,
        max_tokens: int = 2000,
    ) -> str:
        """Send a prompt to the configured LLM and return the text response.

        Returns empty string if AI is disabled (callers must handle this gracefully).
        """
        if not self.enabled:
            logger.debug("AI disabled — skipping completion")
            return ""

        try:
            import litellm  # type: ignore[import-untyped]

            messages: list[_Message] = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            effective_temperature = (
                temperature if temperature is not None else self.config.temperature
            )

            kwargs: dict[str, str | int | float | list[_Message]] = {
                "model": self.config.model,
                "messages": messages,
                "temperature": effective_temperature,
                "max_tokens": max_tokens,
            }
            if self.config.base_url:
                kwargs["api_base"] = self.config.base_url

            response = litellm.completion(**kwargs)
            return str(response.choices[0].message.content or "")

        except Exception as exc:  # noqa: BLE001 — LiteLLM raises many provider-specific types
            logger.warning("AI completion failed: %s", exc)
            return ""

    @classmethod
    def from_meta(cls) -> "AIProvider":
        """Create an AIProvider from the current meta.json config."""
        from resumeforge.data.store import get_meta

        return cls(get_meta().ai)
