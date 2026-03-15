"""Tests for the AI provider layer — uses a mocked litellm.completion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from resumeforge.ai.provider import AIProvider
from resumeforge.ai.rewriter import SectionRewriter
from resumeforge.ai.style import StyleController
from resumeforge.ai.tailor import ResumeTailor
from resumeforge.data.schema import (
    AIConfig,
    Bullet,
    Certifications,
    Education,
    Experience,
    JobDescription,
    Meta,
    Position,
    Profile,
    Projects,
    ResumeContext,
    Skills,
    SkillCategory,
    StyleConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ai_config(enabled: bool = True) -> AIConfig:
    return AIConfig(
        provider="openai",
        model="gpt-4o",
        base_url=None,
        temperature=0.3,
        enabled=enabled,
    )


def _make_style_config(**overrides: object) -> StyleConfig:
    defaults: dict[str, object] = {
        "tone": "professional",
        "max_pages": 1,
        "bullet_style": "action-verb-first",
        "avoid_tool_names_in_bullets": True,
    }
    defaults.update(overrides)
    return StyleConfig.model_validate(defaults)


def _make_resume_context() -> ResumeContext:
    profile = Profile(
        name="Jane Doe",
        title="Security Engineer",
        email="jane@example.com",
        summary="Experienced security engineer with 5 years in cloud security.",
        languages=["en"],
    )
    experience = Experience(
        positions=[
            Position(
                company="Acme Corp",
                title="Security Engineer",
                start_date="2020-01",
                bullets=[
                    Bullet(text="Implemented SIEM solution reducing MTTR by 40%."),
                    Bullet(text="Led penetration testing for 3 major client environments."),
                ],
            )
        ]
    )
    skills = Skills(
        categories=[
            SkillCategory(label="Cloud Security", items=["AWS", "Azure", "GCP"]),
        ]
    )
    return ResumeContext(
        profile=profile,
        experience=experience,
        skills=skills,
        education=Education(),
        projects=Projects(),
        certifications=Certifications(),
        meta=Meta(),
    )


def _make_job() -> JobDescription:
    return JobDescription(
        slug="test-job",
        title="Senior Security Engineer",
        company="BigCorp",
        description="We need a senior security engineer with cloud experience.",
        requirements=["AWS", "Kubernetes", "SIEM"],
        nice_to_have=["Python", "Penetration Testing"],
    )


def _mock_litellm_response(content: str) -> MagicMock:
    """Build a minimal mock that mimics litellm.completion() return value."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# AIProvider tests
# ---------------------------------------------------------------------------


class TestAIProviderDisabled:
    """When ai.enabled=False, complete() must return '' without calling litellm."""

    def test_enabled_property_false(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        assert provider.enabled is False

    def test_complete_returns_empty_string(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        with patch("litellm.completion") as mock_completion:
            result = provider.complete("some prompt")
        assert result == ""
        mock_completion.assert_not_called()

    def test_complete_does_not_raise(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        # Should never raise even with weird inputs
        result = provider.complete("")
        assert isinstance(result, str)


class TestAIProviderEnabled:
    """When ai.enabled=True, complete() must call litellm with the right parameters."""

    def test_enabled_property_true(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        assert provider.enabled is True

    def test_complete_calls_litellm(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        mock_response = _mock_litellm_response("Rewrote the bullet.")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            result = provider.complete("rewrite this")

        mock_completion.assert_called_once()
        assert result == "Rewrote the bullet."

    def test_complete_uses_model_from_config(self) -> None:
        config = _make_ai_config(enabled=True)
        config.model = "gpt-4o-mini"
        provider = AIProvider(config)
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("hello")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_complete_uses_temperature_from_config(self) -> None:
        config = _make_ai_config(enabled=True)
        config.temperature = 0.7
        provider = AIProvider(config)
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("hello")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    def test_complete_temperature_override(self) -> None:
        """Explicit temperature param overrides the config value."""
        provider = AIProvider(_make_ai_config(enabled=True))
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("hello", temperature=0.1)

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.1

    def test_complete_passes_base_url_when_set(self) -> None:
        config = _make_ai_config(enabled=True)
        config.base_url = "http://localhost:11434"
        provider = AIProvider(config)
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("hello")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs.get("api_base") == "http://localhost:11434"

    def test_complete_no_base_url_when_none(self) -> None:
        config = _make_ai_config(enabled=True)
        config.base_url = None
        provider = AIProvider(config)
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("hello")

        call_kwargs = mock_completion.call_args[1]
        assert "api_base" not in call_kwargs

    def test_complete_returns_empty_on_exception(self) -> None:
        """LiteLLM errors must be swallowed and return empty string."""
        provider = AIProvider(_make_ai_config(enabled=True))

        with patch("litellm.completion", side_effect=RuntimeError("network error")):
            result = provider.complete("hello")

        assert result == ""

    def test_complete_includes_system_and_user_messages(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        mock_response = _mock_litellm_response("ok")

        with patch("litellm.completion", return_value=mock_response) as mock_completion:
            provider.complete("user prompt", system="You are a helpful assistant.")

        call_kwargs = mock_completion.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "user prompt"

    def test_complete_handles_none_content_response(self) -> None:
        """If LLM returns None content, result should be empty string."""
        provider = AIProvider(_make_ai_config(enabled=True))
        mock_response = _mock_litellm_response(None)  # type: ignore[arg-type]

        with patch("litellm.completion", return_value=mock_response):
            result = provider.complete("hello")

        assert result == ""


# ---------------------------------------------------------------------------
# StyleController tests
# ---------------------------------------------------------------------------


class TestStyleController:
    def test_default_tone(self) -> None:
        ctrl = StyleController(_make_style_config(tone="professional"))
        assert ctrl.tone == "professional"

    def test_technical_tone(self) -> None:
        ctrl = StyleController(_make_style_config(tone="technical"))
        assert ctrl.tone == "technical"

    def test_invalid_tone_falls_back_to_professional(self) -> None:
        ctrl = StyleController(_make_style_config(tone="aggressive"))
        assert ctrl.tone == "professional"

    def test_bullet_style(self) -> None:
        ctrl = StyleController(_make_style_config(bullet_style="result-first"))
        assert ctrl.bullet_style == "result-first"

    def test_invalid_bullet_style_falls_back(self) -> None:
        ctrl = StyleController(_make_style_config(bullet_style="unknown"))
        assert ctrl.bullet_style == "action-verb-first"

    def test_max_pages_minimum_one(self) -> None:
        ctrl = StyleController(_make_style_config(max_pages=0))
        assert ctrl.max_pages == 1

    def test_max_pages_normal(self) -> None:
        ctrl = StyleController(_make_style_config(max_pages=2))
        assert ctrl.max_pages == 2

    def test_avoid_tool_names_default_true(self) -> None:
        ctrl = StyleController(_make_style_config(avoid_tool_names_in_bullets=True))
        assert ctrl.avoid_tool_names_in_bullets is True

    def test_prompt_context_keys(self) -> None:
        ctrl = StyleController(_make_style_config())
        ctx = ctrl.prompt_context()
        assert "tone" in ctx
        assert "bullet_style" in ctx
        assert "max_pages" in ctx
        assert "avoid_tool_names" in ctx

    def test_tone_instruction_returns_string(self) -> None:
        ctrl = StyleController(_make_style_config(tone="technical"))
        instruction = ctrl.tone_instruction()
        assert isinstance(instruction, str)
        assert len(instruction) > 0

    def test_tone_instruction_professional(self) -> None:
        ctrl = StyleController(_make_style_config(tone="professional"))
        assert "formal" in ctrl.tone_instruction().lower()


# ---------------------------------------------------------------------------
# SectionRewriter tests
# ---------------------------------------------------------------------------


class TestSectionRewriterDisabled:
    def test_rewrite_bullet_returns_original_when_disabled(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        style = _make_style_config()
        rewriter = SectionRewriter(provider, style)
        original = Bullet(text="Built a cloud monitoring solution.")

        with patch("litellm.completion") as mock_completion:
            result = rewriter.rewrite_bullet(original)

        assert result == original
        mock_completion.assert_not_called()

    def test_rewrite_bullets_returns_originals_when_disabled(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        rewriter = SectionRewriter(provider, _make_style_config())
        bullets = [
            Bullet(text="First bullet."),
            Bullet(text="Second bullet."),
        ]
        result = rewriter.rewrite_bullets(bullets)
        assert result == bullets


class TestSectionRewriterEnabled:
    def test_rewrite_bullet_returns_ai_text(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        rewriter = SectionRewriter(provider, _make_style_config())
        original = Bullet(text="Did security stuff.")
        mock_response = _mock_litellm_response("Architected and deployed end-to-end SIEM solution.")

        with patch("litellm.completion", return_value=mock_response):
            result = rewriter.rewrite_bullet(original)

        assert result.text == "Architected and deployed end-to-end SIEM solution."

    def test_rewrite_bullet_preserves_id_and_tags(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        rewriter = SectionRewriter(provider, _make_style_config())
        original = Bullet(id="abc123", text="Old text.", tags=["cloud", "security"], metrics=True)
        mock_response = _mock_litellm_response("New improved text.")

        with patch("litellm.completion", return_value=mock_response):
            result = rewriter.rewrite_bullet(original)

        assert result.id == "abc123"
        assert result.tags == ["cloud", "security"]
        assert result.metrics is True

    def test_rewrite_bullet_falls_back_on_empty_ai_response(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        rewriter = SectionRewriter(provider, _make_style_config())
        original = Bullet(text="Original text.")
        mock_response = _mock_litellm_response("")

        with patch("litellm.completion", return_value=mock_response):
            result = rewriter.rewrite_bullet(original)

        assert result == original

    def test_rewrite_bullets_rewrites_all(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        rewriter = SectionRewriter(provider, _make_style_config())
        bullets = [Bullet(text="First."), Bullet(text="Second.")]

        responses = [
            _mock_litellm_response("Rewrote first."),
            _mock_litellm_response("Rewrote second."),
        ]

        with patch("litellm.completion", side_effect=responses):
            result = rewriter.rewrite_bullets(bullets)

        assert len(result) == 2
        assert result[0].text == "Rewrote first."
        assert result[1].text == "Rewrote second."

    def test_rewrite_bullet_strips_whitespace(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        rewriter = SectionRewriter(provider, _make_style_config())
        original = Bullet(text="Old text.")
        mock_response = _mock_litellm_response("  Leading and trailing spaces.  ")

        with patch("litellm.completion", return_value=mock_response):
            result = rewriter.rewrite_bullet(original)

        assert result.text == "Leading and trailing spaces."


# ---------------------------------------------------------------------------
# ResumeTailor tests
# ---------------------------------------------------------------------------


class TestResumeTailorDisabled:
    def test_generate_summary_returns_existing_when_disabled(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()

        with patch("litellm.completion") as mock_completion:
            result = tailor.generate_summary(context, job)

        assert result == context.profile.summary
        mock_completion.assert_not_called()

    def test_suggest_keywords_works_without_ai(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        # "Kubernetes" and "SIEM" are not in the resume context
        missing = tailor.suggest_keywords(context, job)
        assert "Kubernetes" in missing

    def test_suggest_keywords_excludes_present_skills(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=False))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        # "AWS" is in the skills, so should NOT be in missing keywords
        missing = tailor.suggest_keywords(context, job)
        assert "AWS" not in missing


class TestResumeTailorEnabled:
    def test_generate_summary_returns_ai_output(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        ai_summary = "Senior Security Engineer with 5+ years securing cloud infrastructure."
        mock_response = _mock_litellm_response(ai_summary)

        with patch("litellm.completion", return_value=mock_response):
            result = tailor.generate_summary(context, job)

        assert result == ai_summary

    def test_generate_summary_strips_whitespace(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        mock_response = _mock_litellm_response("  AI summary with spaces.  ")

        with patch("litellm.completion", return_value=mock_response):
            result = tailor.generate_summary(context, job)

        assert result == "AI summary with spaces."

    def test_generate_summary_falls_back_on_empty_response(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        mock_response = _mock_litellm_response("")

        with patch("litellm.completion", return_value=mock_response):
            result = tailor.generate_summary(context, job)

        assert result == context.profile.summary

    def test_suggest_keywords_returns_list_of_strings(self) -> None:
        provider = AIProvider(_make_ai_config(enabled=True))
        tailor = ResumeTailor(provider)
        context = _make_resume_context()
        job = _make_job()
        missing = tailor.suggest_keywords(context, job)
        assert isinstance(missing, list)
        assert all(isinstance(k, str) for k in missing)


# ---------------------------------------------------------------------------
# Prompt template rendering tests (no LiteLLM call needed)
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Verify that all .j2 templates render without error given valid context."""

    def _render(self, template_name: str, **kwargs: object) -> str:
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader

        prompts_dir = (
            Path(__file__).parent.parent / "resumeforge" / "ai" / "prompts"
        )
        env = Environment(loader=FileSystemLoader(str(prompts_dir)), autoescape=False)
        tmpl = env.get_template(template_name)
        return tmpl.render(**kwargs)

    def test_rewrite_section_renders(self) -> None:
        out = self._render(
            "rewrite_section.j2",
            bullet="Built monitoring dashboards.",
            tone="professional",
            bullet_style="action-verb-first",
            avoid_tool_names=True,
        )
        assert "Built monitoring dashboards." in out

    def test_tailor_to_job_renders(self) -> None:
        context = _make_resume_context()
        job = _make_job()
        out = self._render(
            "tailor_to_job.j2",
            profile=context.profile,
            experience=context.experience,
            skills=context.skills,
            job_title=job.title,
            job_company=job.company,
            job_description=job.description,
            requirements=job.requirements,
        )
        assert "Senior Security Engineer" in out

    def test_translate_renders(self) -> None:
        out = self._render(
            "translate.j2",
            content="Implemented cloud security controls.",
            source_lang="en",
            target_lang="he",
            rtl=True,
            section_type="bullet",
        )
        assert "Implemented cloud security controls." in out

    def test_analyze_renders(self) -> None:
        out = self._render(
            "analyze.j2",
            content="Managed team and did stuff.",
            section_label="Professional Summary",
            tone="professional",
            language="en",
            checks=["grammar", "clarity"],
        )
        assert "grammar" in out
        assert "clarity" in out

    def test_suggest_bullets_renders(self) -> None:
        out = self._render(
            "suggest_bullets.j2",
            raw_notes="Worked on AWS infrastructure, reduced costs, automated deployments.",
            job_title="Cloud Engineer",
            company="Acme Corp",
            tone="professional",
            bullet_style="action-verb-first",
            count=4,
            avoid_tool_names=False,
        )
        assert "Cloud Engineer" in out

    def test_gap_fill_renders(self) -> None:
        out = self._render(
            "gap_fill.j2",
            missing_skills=["Kubernetes", "Terraform"],
            profile_summary="Security engineer with 5 years experience.",
            experience_titles=["Security Engineer", "SOC Analyst"],
            job_title="Senior DevSecOps Engineer",
            job_company="BigCorp",
            tone="professional",
        )
        assert "Kubernetes" in out
        assert "Terraform" in out
