"""StyleController — manages tone, bullet_style, and max_pages from meta.json style config."""

from __future__ import annotations

from resumeforge.data.schema import StyleConfig

# Valid tone values
VALID_TONES = frozenset({"professional", "technical", "creative"})

# Valid bullet style values
VALID_BULLET_STYLES = frozenset({"action-verb-first", "result-first", "context-action-result"})


class StyleController:
    """Centralises all style-related decisions for AI prompts and resume rendering.

    Reads from a StyleConfig (sourced from meta.json). Provides validated access
    to tone, bullet_style, and max_pages, plus helper methods used by rewriter.py
    and tailor.py when constructing prompts.
    """

    def __init__(self, style: StyleConfig) -> None:
        self._style = style

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tone(self) -> str:
        """Tone string — one of 'professional', 'technical', 'creative'."""
        if self._style.tone in VALID_TONES:
            return self._style.tone
        return "professional"

    @property
    def bullet_style(self) -> str:
        """Bullet formatting convention."""
        if self._style.bullet_style in VALID_BULLET_STYLES:
            return self._style.bullet_style
        return "action-verb-first"

    @property
    def max_pages(self) -> int:
        """Maximum page count — enforced as a positive integer."""
        return max(1, self._style.max_pages)

    @property
    def avoid_tool_names_in_bullets(self) -> bool:
        """Whether to suppress specific tool/product names in bullet points."""
        return self._style.avoid_tool_names_in_bullets

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def prompt_context(self) -> dict[str, str | bool | int]:
        """Return a dict of style keys ready to inject into any prompt template."""
        return {
            "tone": self.tone,
            "bullet_style": self.bullet_style,
            "max_pages": self.max_pages,
            "avoid_tool_names": self.avoid_tool_names_in_bullets,
        }

    def tone_instruction(self) -> str:
        """Return a human-readable tone instruction sentence for embedding in prompts."""
        instructions: dict[str, str] = {
            "professional": "Use formal, polished language appropriate for corporate environments.",
            "technical": "Emphasise technical depth, precision, and domain-specific terminology.",
            "creative": "Use dynamic, engaging language that showcases personality and innovation.",
        }
        return instructions.get(self.tone, instructions["professional"])

    @classmethod
    def from_meta(cls) -> StyleController:
        """Create a StyleController from the current meta.json config."""
        from resumeforge.data.store import get_meta

        return cls(get_meta().style)
