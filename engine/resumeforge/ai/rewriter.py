"""Section rewriter — AI-powered rewriting with style control."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from resumeforge.ai.provider import AIProvider
from resumeforge.data.schema import Bullet, StyleConfig

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _render_prompt(template_name: str, **kwargs: object) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), autoescape=False)
    tmpl = env.get_template(template_name)
    return tmpl.render(**kwargs)


class SectionRewriter:
    """Rewrites resume bullets / sections using AI."""

    def __init__(self, provider: AIProvider, style: StyleConfig) -> None:
        self.provider = provider
        self.style = style

    def rewrite_bullet(self, bullet: Bullet) -> Bullet:
        """Rewrite a single bullet point. Returns original if AI disabled."""
        if not self.provider.enabled:
            return bullet

        prompt = _render_prompt(
            "rewrite_section.j2",
            bullet=bullet.text,
            tone=self.style.tone,
            bullet_style=self.style.bullet_style,
            avoid_tool_names=self.style.avoid_tool_names_in_bullets,
        )
        result = self.provider.complete(prompt)
        if result:
            return bullet.model_copy(update={"text": result.strip()})
        return bullet

    def rewrite_bullets(self, bullets: list[Bullet]) -> list[Bullet]:
        """Rewrite all bullets. Returns originals if AI disabled."""
        return [self.rewrite_bullet(b) for b in bullets]
