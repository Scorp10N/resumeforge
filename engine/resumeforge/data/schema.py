"""Data schemas — all Pydantic models for resume data."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"


def _uid() -> str:
    return str(uuid4())[:8]


class VersionedModel(BaseModel):
    schema_version: str = SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class Profile(VersionedModel):
    """Personal / contact information. Stored in data/profile.json (PII — gitignored)."""

    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""
    languages: list[str] = Field(default_factory=lambda: ["en"])
    summary: str = ""


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


class Bullet(BaseModel):
    id: str = Field(default_factory=_uid)
    text: str
    tags: list[str] = Field(default_factory=list)
    metrics: bool = False  # True if bullet contains quantifiable metrics


class Position(BaseModel):
    id: str = Field(default_factory=_uid)
    company: str
    title: str
    start_date: str  # YYYY-MM
    end_date: str | None = None  # None = current
    is_current: bool = False
    location: str = ""
    bullets: list[Bullet] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: int = 1  # lower = higher priority in output

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v: object) -> object:
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("start_date must be YYYY-MM or YYYY-MM-DD format")

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("end_date must be YYYY-MM or YYYY-MM-DD format")

    @model_validator(mode="after")
    def check_is_current_consistency(self) -> Position:
        if self.is_current and self.end_date is not None:
            raise ValueError("is_current=True positions must have end_date=None")
        return self


class Experience(VersionedModel):
    positions: list[Position] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class SkillCategory(BaseModel):
    id: str = Field(default_factory=_uid)
    label: str
    items: list[str] = Field(default_factory=list)
    priority: int = 1


class ExploringItem(BaseModel):
    label: str
    items: list[str] = Field(default_factory=list)


class Skills(VersionedModel):
    categories: list[SkillCategory] = Field(default_factory=list)
    exploring: list[ExploringItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


class EducationEntry(BaseModel):
    id: str = Field(default_factory=_uid)
    institution: str
    degree: str
    field: str = ""
    start_date: str  # YYYY-MM
    end_date: str | None = None
    gpa: str = ""
    location: str = ""
    notes: list[str] = Field(default_factory=list)
    priority: int = 1

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v: object) -> object:
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("start_date must be YYYY-MM or YYYY-MM-DD format")

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("end_date must be YYYY-MM or YYYY-MM-DD format")


class Education(VersionedModel):
    entries: list[EducationEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class Project(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    description: str
    bullets: list[Bullet] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    url: str = ""
    date: str = ""  # YYYY-MM
    tags: list[str] = Field(default_factory=list)
    priority: int = 1


class Projects(VersionedModel):
    projects: list[Project] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


class Certification(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    issuer: str
    date: str  # YYYY-MM
    expiry: str | None = None
    url: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: object) -> object:
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("date must be YYYY-MM or YYYY-MM-DD format")

    @field_validator("expiry", mode="before")
    @classmethod
    def validate_expiry(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, str) and len(v) >= 7:
            return v
        raise ValueError("expiry must be YYYY-MM or YYYY-MM-DD format")


class Certifications(VersionedModel):
    certifications: list[Certification] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Job description (used for tailoring + ATS)
# ---------------------------------------------------------------------------


class JobDescription(BaseModel):
    slug: str
    title: str
    company: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    language: str = "en"
    saved_date: str = Field(default_factory=lambda: date.today().isoformat())
    notes: str = ""

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: object) -> object:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("slug must be a non-empty string")
        return v


# ---------------------------------------------------------------------------
# Engine config (meta.json)
# ---------------------------------------------------------------------------


class EngineConfig(BaseModel):
    mode: str = "local"  # "local" | "cloud" | "hybrid"
    url: str | None = None
    port: int = 8080

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: object) -> object:
        allowed = {"local", "cloud", "hybrid"}
        if isinstance(v, str) and v in allowed:
            return v
        raise ValueError(f"mode must be one of {allowed}")

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v: object) -> object:
        if isinstance(v, int) and 1 <= v <= 65535:
            return v
        raise ValueError("port must be between 1 and 65535")


class AIConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str | None = None
    temperature: float = 0.3
    enabled: bool = False

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature(cls, v: object) -> object:
        if isinstance(v, (int, float)) and 0.0 <= float(v) <= 2.0:
            return float(v)
        raise ValueError("temperature must be between 0.0 and 2.0")


class StyleConfig(BaseModel):
    tone: str = "professional"  # "professional" | "technical" | "creative"
    max_pages: int = 1
    bullet_style: str = "action-verb-first"
    avoid_tool_names_in_bullets: bool = True

    @field_validator("tone", mode="before")
    @classmethod
    def validate_tone(cls, v: object) -> object:
        allowed = {"professional", "technical", "creative"}
        if isinstance(v, str) and v in allowed:
            return v
        raise ValueError(f"tone must be one of {allowed}")

    @field_validator("max_pages", mode="before")
    @classmethod
    def validate_max_pages(cls, v: object) -> object:
        if isinstance(v, int) and v >= 1:
            return v
        raise ValueError("max_pages must be a positive integer")


class Meta(VersionedModel):
    default_locale: str = "en"
    default_template: str = "classic"
    default_format: str = "pdf"
    engine: EngineConfig = Field(default_factory=EngineConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)


# ---------------------------------------------------------------------------
# Resume context (assembled build input)
# ---------------------------------------------------------------------------


class ResumeContext(BaseModel):
    """Fully assembled, ready-to-render resume data."""

    profile: Profile
    experience: Experience
    skills: Skills
    education: Education
    projects: Projects
    certifications: Certifications
    meta: Meta
    job: JobDescription | None = None
    locale: str = "en"
    template_name: str = "classic"
    output_format: str = "pdf"
