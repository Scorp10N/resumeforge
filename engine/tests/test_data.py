"""Comprehensive tests for data schemas, store CRUD, and migrations."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from resumeforge.data.migrations import migrate, migrate_file, needs_migration
from resumeforge.data.schema import (
    AIConfig,
    Bullet,
    Certification,
    Certifications,
    Education,
    EducationEntry,
    EngineConfig,
    Experience,
    JobDescription,
    Meta,
    Position,
    Profile,
    Project,
    Projects,
    ResumeContext,
    Skills,
    SkillCategory,
    StyleConfig,
    SCHEMA_VERSION,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _patch_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect all store path constants to tmp_path."""
    import resumeforge.data.store as store_module

    monkeypatch.setattr(store_module, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(store_module, "JOBS_DIR", tmp_path / "data" / "jobs")
    monkeypatch.setattr(store_module, "OUTPUT_DIR", tmp_path / "output")


# ===========================================================================
# Schema — Profile
# ===========================================================================


class TestProfile:
    def test_defaults(self) -> None:
        p = Profile()
        assert p.schema_version == "1.0"
        assert p.languages == ["en"]
        assert p.name == ""
        assert p.email == ""
        assert p.summary == ""

    def test_full_profile(self) -> None:
        p = Profile(
            name="Alex Placeholder",
            email="alex@example.com",
            title="Platform Engineer",
            phone="+1-555-000-0000",
            linkedin="linkedin.com/in/alex",
            github="github.com/alex",
            location="San Francisco, CA",
            languages=["en", "fr"],
            summary="Experienced engineer.",
        )
        assert p.name == "Alex Placeholder"
        assert p.title == "Platform Engineer"
        assert p.languages == ["en", "fr"]

    def test_roundtrip_json(self) -> None:
        p = Profile(name="Test User", email="test@test.com")
        restored = Profile.model_validate_json(p.model_dump_json())
        assert restored.name == p.name
        assert restored.email == p.email
        assert restored.schema_version == SCHEMA_VERSION

    def test_schema_version_preserved(self) -> None:
        raw = {"schema_version": "1.0", "name": "Test"}
        p = Profile.model_validate(raw)
        assert p.schema_version == "1.0"


# ===========================================================================
# Schema — Bullet
# ===========================================================================


class TestBullet:
    def test_bullet_defaults(self) -> None:
        b = Bullet(text="Did something important.")
        assert b.text == "Did something important."
        assert b.metrics is False
        assert b.tags == []
        assert len(b.id) == 8

    def test_bullet_with_metrics(self) -> None:
        b = Bullet(text="Reduced latency by 40%.", metrics=True, tags=["performance"])
        assert b.metrics is True
        assert "performance" in b.tags

    def test_bullet_requires_text(self) -> None:
        with pytest.raises(ValidationError):
            Bullet()  # type: ignore[call-arg]


# ===========================================================================
# Schema — Position / Experience
# ===========================================================================


class TestPosition:
    def test_minimal_position(self) -> None:
        pos = Position(company="Acme", title="Engineer", start_date="2023-01")
        assert pos.company == "Acme"
        assert pos.end_date is None
        assert pos.is_current is False

    def test_position_with_bullets(self) -> None:
        pos = Position(
            company="Acme",
            title="Engineer",
            start_date="2023-01",
            bullets=[
                Bullet(text="Built a thing"),
                Bullet(text="Improved performance by 40%", metrics=True),
            ],
        )
        assert len(pos.bullets) == 2
        assert pos.bullets[1].metrics is True

    def test_date_format_yyyy_mm(self) -> None:
        pos = Position(company="X", title="Y", start_date="2022-06", end_date="2023-12")
        assert pos.start_date == "2022-06"
        assert pos.end_date == "2023-12"

    def test_date_format_yyyy_mm_dd(self) -> None:
        pos = Position(company="X", title="Y", start_date="2022-06-15")
        assert pos.start_date == "2022-06-15"

    def test_end_date_none_allowed(self) -> None:
        pos = Position(company="X", title="Y", start_date="2022-06")
        assert pos.end_date is None

    def test_invalid_start_date_raises(self) -> None:
        with pytest.raises(ValidationError):
            Position(company="X", title="Y", start_date="2022")  # too short

    def test_is_current_true_requires_no_end_date(self) -> None:
        with pytest.raises(ValidationError):
            Position(
                company="X",
                title="Y",
                start_date="2022-06",
                end_date="2024-01",
                is_current=True,
            )

    def test_is_current_no_end_date_valid(self) -> None:
        pos = Position(company="X", title="Y", start_date="2022-06", is_current=True)
        assert pos.end_date is None

    def test_experience_serialization(self) -> None:
        exp = Experience(
            positions=[Position(company="Corp", title="Dev", start_date="2020-01")]
        )
        data = json.loads(exp.model_dump_json())
        assert data["positions"][0]["company"] == "Corp"
        assert data["schema_version"] == SCHEMA_VERSION

    def test_experience_empty_default(self) -> None:
        exp = Experience()
        assert exp.positions == []


# ===========================================================================
# Schema — Skills
# ===========================================================================


class TestSkills:
    def test_skill_category_defaults(self) -> None:
        cat = SkillCategory(label="Cloud")
        assert cat.items == []
        assert cat.priority == 1
        assert len(cat.id) == 8

    def test_skills_with_categories(self) -> None:
        skills = Skills(
            categories=[
                SkillCategory(label="Cloud", items=["AWS", "Azure"], priority=1),
                SkillCategory(label="Languages", items=["Python", "Go"], priority=2),
            ]
        )
        assert len(skills.categories) == 2
        assert "AWS" in skills.categories[0].items

    def test_skills_exploring(self) -> None:
        from resumeforge.data.schema import ExploringItem

        skills = Skills(
            exploring=[ExploringItem(label="AI", items=["LangChain", "LiteLLM"])]
        )
        assert skills.exploring[0].label == "AI"
        assert "LiteLLM" in skills.exploring[0].items

    def test_skills_empty_defaults(self) -> None:
        skills = Skills()
        assert skills.categories == []
        assert skills.exploring == []

    def test_skills_roundtrip(self) -> None:
        skills = Skills(
            categories=[SkillCategory(label="Cloud", items=["AWS"])]
        )
        restored = Skills.model_validate_json(skills.model_dump_json())
        assert restored.categories[0].label == "Cloud"


# ===========================================================================
# Schema — Education
# ===========================================================================


class TestEducation:
    def test_education_entry(self) -> None:
        entry = EducationEntry(
            institution="State University",
            degree="B.Sc.",
            field="Computer Science",
            start_date="2016-09",
            end_date="2020-05",
            gpa="3.8",
            location="Placeholder City",
            notes=["Dean's List 2019"],
        )
        assert entry.institution == "State University"
        assert entry.gpa == "3.8"
        assert len(entry.notes) == 1

    def test_education_entry_invalid_start_date(self) -> None:
        with pytest.raises(ValidationError):
            EducationEntry(
                institution="U",
                degree="B.Sc.",
                start_date="16-09",  # invalid
            )

    def test_education_entry_no_end_date(self) -> None:
        entry = EducationEntry(
            institution="U", degree="B.Sc.", start_date="2020-09"
        )
        assert entry.end_date is None

    def test_education_container_defaults(self) -> None:
        edu = Education()
        assert edu.entries == []
        assert edu.schema_version == SCHEMA_VERSION

    def test_education_roundtrip(self) -> None:
        edu = Education(
            entries=[
                EducationEntry(
                    institution="Tech U",
                    degree="M.Sc.",
                    start_date="2020-09",
                    end_date="2022-06",
                )
            ]
        )
        restored = Education.model_validate_json(edu.model_dump_json())
        assert restored.entries[0].institution == "Tech U"


# ===========================================================================
# Schema — Projects
# ===========================================================================


class TestProjects:
    def test_project_defaults(self) -> None:
        proj = Project(name="MyApp", description="A cool app.")
        assert proj.technologies == []
        assert proj.tags == []
        assert proj.url == ""
        assert proj.priority == 1

    def test_project_full(self) -> None:
        proj = Project(
            name="ResumeForge",
            description="Resume automation.",
            bullets=[Bullet(text="Built the engine.")],
            technologies=["Python", "Go"],
            url="https://github.com/example/rf",
            date="2025-03",
            tags=["open-source"],
        )
        assert proj.technologies == ["Python", "Go"]
        assert len(proj.bullets) == 1

    def test_projects_container_defaults(self) -> None:
        p = Projects()
        assert p.projects == []

    def test_projects_roundtrip(self) -> None:
        p = Projects(
            projects=[Project(name="App", description="Desc")]
        )
        restored = Projects.model_validate_json(p.model_dump_json())
        assert restored.projects[0].name == "App"


# ===========================================================================
# Schema — Certifications
# ===========================================================================


class TestCertifications:
    def test_certification_valid(self) -> None:
        cert = Certification(
            name="AWS Solutions Architect",
            issuer="Amazon Web Services",
            date="2024-01",
            expiry="2027-01",
            url="https://aws.amazon.com/certification/",
            tags=["cloud", "aws"],
        )
        assert cert.issuer == "Amazon Web Services"
        assert cert.expiry == "2027-01"

    def test_certification_no_expiry(self) -> None:
        cert = Certification(name="CKA", issuer="CNCF", date="2023-06")
        assert cert.expiry is None

    def test_certification_invalid_date(self) -> None:
        with pytest.raises(ValidationError):
            Certification(name="X", issuer="Y", date="2024")  # too short

    def test_certifications_container_empty(self) -> None:
        c = Certifications()
        assert c.certifications == []


# ===========================================================================
# Schema — JobDescription
# ===========================================================================


class TestJobDescription:
    def test_job_full(self) -> None:
        job = JobDescription(
            slug="bank-appsec",
            title="Senior AppSec Engineer",
            company="Major Bank",
            description="Looking for a senior engineer...",
            requirements=["SAST/DAST", "Kubernetes", "Python"],
            nice_to_have=["Penetration Testing"],
            language="en",
            notes="High priority role",
        )
        assert job.slug == "bank-appsec"
        assert "SAST/DAST" in job.requirements
        assert job.language == "en"

    def test_job_empty_slug_raises(self) -> None:
        with pytest.raises(ValidationError):
            JobDescription(slug="", title="Dev", company="Corp", description="...")

    def test_job_saved_date_default(self) -> None:
        job = JobDescription(
            slug="test-job", title="Dev", company="Corp", description="..."
        )
        # saved_date should be a valid ISO date string
        from datetime import date

        date.fromisoformat(job.saved_date)

    def test_job_roundtrip(self) -> None:
        job = JobDescription(
            slug="test-role",
            title="Engineer",
            company="Corp",
            description="Job desc",
            requirements=["Python"],
        )
        restored = JobDescription.model_validate_json(job.model_dump_json())
        assert restored.slug == "test-role"
        assert "Python" in restored.requirements


# ===========================================================================
# Schema — Meta / Config
# ===========================================================================


class TestMeta:
    def test_defaults(self) -> None:
        meta = Meta()
        assert meta.default_template == "classic"
        assert meta.default_format == "pdf"
        assert meta.ai.enabled is False
        assert meta.engine.port == 8080
        assert meta.engine.mode == "local"
        assert meta.style.tone == "professional"
        assert meta.schema_version == SCHEMA_VERSION

    def test_engine_config_invalid_mode(self) -> None:
        with pytest.raises(ValidationError):
            EngineConfig(mode="serverless")

    def test_engine_config_invalid_port(self) -> None:
        with pytest.raises(ValidationError):
            EngineConfig(port=0)

    def test_engine_config_valid_modes(self) -> None:
        for mode in ("local", "cloud", "hybrid"):
            cfg = EngineConfig(mode=mode)
            assert cfg.mode == mode

    def test_ai_config_temperature_bounds(self) -> None:
        ai = AIConfig(temperature=0.0)
        assert ai.temperature == 0.0
        ai = AIConfig(temperature=2.0)
        assert ai.temperature == 2.0

    def test_ai_config_invalid_temperature(self) -> None:
        with pytest.raises(ValidationError):
            AIConfig(temperature=2.5)

    def test_style_config_invalid_tone(self) -> None:
        with pytest.raises(ValidationError):
            StyleConfig(tone="aggressive")

    def test_style_config_invalid_max_pages(self) -> None:
        with pytest.raises(ValidationError):
            StyleConfig(max_pages=0)

    def test_meta_roundtrip(self) -> None:
        meta = Meta()
        restored = Meta.model_validate_json(meta.model_dump_json())
        assert restored.engine.port == 8080
        assert restored.ai.model == "gpt-4o"

    def test_meta_custom_values(self) -> None:
        meta = Meta(
            default_locale="he",
            default_template="modern",
            engine=EngineConfig(mode="cloud", port=443),
            ai=AIConfig(provider="anthropic", model="claude-opus-4-20250514", enabled=True),
            style=StyleConfig(tone="technical", max_pages=2),
        )
        assert meta.default_locale == "he"
        assert meta.engine.mode == "cloud"
        assert meta.ai.enabled is True
        assert meta.style.max_pages == 2


# ===========================================================================
# Schema — ResumeContext
# ===========================================================================


class TestResumeContext:
    def test_resume_context_minimal(self) -> None:
        ctx = ResumeContext(
            profile=Profile(),
            experience=Experience(),
            skills=Skills(),
            education=Education(),
            projects=Projects(),
            certifications=Certifications(),
            meta=Meta(),
        )
        assert ctx.job is None
        assert ctx.locale == "en"
        assert ctx.template_name == "classic"
        assert ctx.output_format == "pdf"

    def test_resume_context_with_job(self) -> None:
        job = JobDescription(
            slug="test", title="Dev", company="Corp", description="..."
        )
        ctx = ResumeContext(
            profile=Profile(name="Test User"),
            experience=Experience(),
            skills=Skills(),
            education=Education(),
            projects=Projects(),
            certifications=Certifications(),
            meta=Meta(),
            job=job,
            locale="he",
        )
        assert ctx.job is not None
        assert ctx.job.slug == "test"
        assert ctx.locale == "he"


# ===========================================================================
# Store — CRUD
# ===========================================================================


class TestStore:
    def test_init_creates_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        store_module.init_data_dir()

        expected = [
            "experience.json",
            "skills.json",
            "education.json",
            "projects.json",
            "certifications.json",
            "meta.json",
        ]
        for f in expected:
            assert (tmp_path / "data" / f).exists(), f"{f} was not created"

    def test_init_does_not_overwrite_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        (tmp_path / "data").mkdir(parents=True)
        existing = tmp_path / "data" / "skills.json"
        existing.write_text('{"schema_version": "1.0", "categories": [], "exploring": [], "_marker": true}')

        store_module.init_data_dir()

        raw = json.loads(existing.read_text())
        assert raw.get("_marker") is True, "init_data_dir must not overwrite existing files"

    def test_save_and_load_profile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        profile = Profile(name="Test User", email="test@example.com", title="Engineer")
        store_module.save_profile(profile)

        loaded = store_module.get_profile()
        assert loaded.name == "Test User"
        assert loaded.email == "test@example.com"
        assert loaded.title == "Engineer"

    def test_get_profile_missing_returns_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        p = store_module.get_profile()
        assert p.name == ""

    def test_save_and_load_experience(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        exp = Experience(
            positions=[Position(company="Acme", title="Engineer", start_date="2023-01")]
        )
        store_module.save_experience(exp)
        loaded = store_module.get_experience()
        assert len(loaded.positions) == 1
        assert loaded.positions[0].company == "Acme"

    def test_save_and_load_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        skills = Skills(categories=[SkillCategory(label="Cloud", items=["AWS"])])
        store_module.save_skills(skills)
        loaded = store_module.get_skills()
        assert loaded.categories[0].label == "Cloud"

    def test_save_and_load_education(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        edu = Education(
            entries=[
                EducationEntry(
                    institution="State U", degree="B.Sc.", start_date="2016-09"
                )
            ]
        )
        store_module.save_education(edu)
        loaded = store_module.get_education()
        assert loaded.entries[0].institution == "State U"

    def test_save_and_load_projects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        projects = Projects(projects=[Project(name="MyApp", description="Cool app.")])
        store_module.save_projects(projects)
        loaded = store_module.get_projects()
        assert loaded.projects[0].name == "MyApp"

    def test_save_and_load_certifications(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        certs = Certifications(
            certifications=[
                Certification(name="CKA", issuer="CNCF", date="2023-06")
            ]
        )
        store_module.save_certifications(certs)
        loaded = store_module.get_certifications()
        assert loaded.certifications[0].name == "CKA"

    def test_save_and_load_meta(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        meta = Meta(default_template="modern")
        store_module.save_meta(meta)
        loaded = store_module.get_meta()
        assert loaded.default_template == "modern"


# ===========================================================================
# Store — Job CRUD
# ===========================================================================


class TestJobCRUD:
    def test_save_get_delete_job(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        job = JobDescription(
            slug="test-role",
            title="Developer",
            company="Corp",
            description="Looking for a developer.",
            requirements=["Python"],
        )
        store_module.save_job(job)

        loaded = store_module.get_job("test-role")
        assert loaded is not None
        assert loaded.title == "Developer"
        assert "Python" in loaded.requirements

        found = store_module.list_jobs()
        assert len(found) == 1

        deleted = store_module.delete_job("test-role")
        assert deleted is True
        assert store_module.get_job("test-role") is None

    def test_get_nonexistent_job_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        assert store_module.get_job("does-not-exist") is None

    def test_delete_nonexistent_job_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        assert store_module.delete_job("ghost") is False

    def test_list_jobs_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        assert store_module.list_jobs() == []

    def test_list_jobs_multiple(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        for slug in ("alpha", "beta", "gamma"):
            store_module.save_job(
                JobDescription(slug=slug, title="Dev", company="Corp", description="...")
            )
        jobs = store_module.list_jobs()
        assert len(jobs) == 3
        slugs = {j.slug for j in jobs}
        assert slugs == {"alpha", "beta", "gamma"}

    def test_list_jobs_skips_malformed_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        store_module._ensure_dirs()
        # Write a broken JSON file
        (tmp_path / "data" / "jobs" / "broken.json").write_text(
            "not valid json", encoding="utf-8"
        )
        # Write a valid job
        store_module.save_job(
            JobDescription(slug="good", title="Dev", company="Corp", description="...")
        )
        jobs = store_module.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].slug == "good"

    def test_save_job_overwrites_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        job = JobDescription(
            slug="role", title="Junior Dev", company="Corp", description="..."
        )
        store_module.save_job(job)

        updated = JobDescription(
            slug="role", title="Senior Dev", company="Corp", description="..."
        )
        store_module.save_job(updated)

        loaded = store_module.get_job("role")
        assert loaded is not None
        assert loaded.title == "Senior Dev"


# ===========================================================================
# Store — Backup (export / import)
# ===========================================================================


class TestBackup:
    def test_export_excludes_profile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        store_module.init_data_dir()
        store_module.save_profile(Profile(name="PII Data"))

        archive = store_module.export_backup(tmp_path / "backup")
        assert archive.suffix == ".zip"

        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        assert "data/profile.json" not in names
        assert "data/meta.json" in names

    def test_export_includes_jobs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        store_module.init_data_dir()
        store_module.save_job(
            JobDescription(slug="role", title="Dev", company="Corp", description="...")
        )

        archive = store_module.export_backup(tmp_path / "backup")
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        assert "data/jobs/role.json" in names

    def test_import_restores_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import resumeforge.data.store as store_module

        _patch_store(monkeypatch, tmp_path)
        store_module.init_data_dir()
        store_module.save_skills(Skills(categories=[SkillCategory(label="Cloud", items=["AWS"])]))
        store_module.save_job(
            JobDescription(slug="job1", title="Dev", company="Corp", description="...")
        )

        archive = store_module.export_backup(tmp_path / "backup")

        # Wipe data dir
        import shutil

        shutil.rmtree(tmp_path / "data")
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "jobs").mkdir()

        restored = store_module.import_backup(archive)
        assert any("skills.json" in r for r in restored)
        assert any("job1.json" in r for r in restored)

        loaded_skills = store_module.get_skills()
        assert loaded_skills.categories[0].label == "Cloud"


# ===========================================================================
# Migrations
# ===========================================================================


class TestMigrations:
    def test_needs_migration_false_for_current(self) -> None:
        data: dict[str, object] = {"schema_version": SCHEMA_VERSION}
        assert needs_migration(data) is False

    def test_needs_migration_true_for_old(self) -> None:
        # Simulate a future version scenario by patching; for now test
        # that a missing schema_version field defaults to "1.0"
        data: dict[str, object] = {}
        # No schema_version key — defaults to "1.0" in needs_migration
        # Since SCHEMA_VERSION is "1.0", this should be False
        assert needs_migration(data) is False

    def test_migrate_same_version_noop(self) -> None:
        data: dict[str, object] = {
            "schema_version": "1.0",
            "name": "Alex",
        }
        result = migrate(data)
        assert result["name"] == "Alex"
        assert result["schema_version"] == "1.0"

    def test_migrate_preserves_all_fields(self) -> None:
        data: dict[str, object] = {
            "schema_version": "1.0",
            "positions": [],
            "extra_field": "preserved",
        }
        result = migrate(data)
        assert result["extra_field"] == "preserved"

    def test_migrate_unknown_version_raises(self) -> None:
        data: dict[str, object] = {"schema_version": "99.0"}
        with pytest.raises(ValueError, match="Unknown schema_version"):
            migrate(data)

    def test_migrate_file_no_change_needed(self, tmp_path: Path) -> None:
        f = tmp_path / "meta.json"
        f.write_text(
            json.dumps({"schema_version": SCHEMA_VERSION, "default_template": "classic"}),
            encoding="utf-8",
        )
        changed = migrate_file(f)
        assert changed is False

    def test_migrate_file_unknown_version_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "meta.json"
        f.write_text(
            json.dumps({"schema_version": "99.0"}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            migrate_file(f)


# ===========================================================================
# Sample data file validation
# ===========================================================================


class TestSampleDataFiles:
    """Validate that the sample data files in engine/data/ parse correctly."""

    _DATA_DIR = Path(__file__).parent.parent / "data"

    def test_profile_json_valid(self) -> None:
        path = self._DATA_DIR / "profile.json"
        assert path.exists(), "engine/data/profile.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        p = Profile.model_validate(raw)
        assert p.name != ""

    def test_experience_json_valid(self) -> None:
        path = self._DATA_DIR / "experience.json"
        assert path.exists(), "engine/data/experience.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = Experience.model_validate(raw)
        assert len(exp.positions) >= 1

    def test_skills_json_valid(self) -> None:
        path = self._DATA_DIR / "skills.json"
        assert path.exists(), "engine/data/skills.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        skills = Skills.model_validate(raw)
        assert len(skills.categories) >= 1

    def test_education_json_valid(self) -> None:
        path = self._DATA_DIR / "education.json"
        assert path.exists(), "engine/data/education.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        edu = Education.model_validate(raw)
        assert len(edu.entries) >= 1

    def test_projects_json_valid(self) -> None:
        path = self._DATA_DIR / "projects.json"
        assert path.exists(), "engine/data/projects.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        projects = Projects.model_validate(raw)
        assert len(projects.projects) >= 1

    def test_meta_json_valid(self) -> None:
        path = self._DATA_DIR / "meta.json"
        assert path.exists(), "engine/data/meta.json is missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = Meta.model_validate(raw)
        assert meta.default_template != ""
