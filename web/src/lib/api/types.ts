// TypeScript types matching the ResumeForge engine OpenAPI schema

// ── Build ──────────────────────────────────────────────────────────────────

export interface BuildRequest {
	template?: string;
	format?: 'md' | 'pdf' | 'docx';
	job_slug?: string;
	lang?: string;
	ai?: boolean;
}

export interface BuildResponse {
	status: 'success' | 'error';
	output_path?: string;
	output_url?: string;
	format?: string;
	template?: string;
	job_slug?: string;
	analysis_summary?: AnalysisSummary;
	error?: string;
}

export interface BuildStreamEvent {
	type: 'progress' | 'step' | 'complete' | 'error';
	message: string;
	step?: string;
	progress?: number;
	output_path?: string;
	error?: string;
}

// ── Analysis ───────────────────────────────────────────────────────────────

export interface AnalysisSummary {
	overall_score: number;
	ats_score?: number;
	issues_count: number;
}

export interface AnalysisFinding {
	severity: 'critical' | 'warning' | 'info';
	category: string;
	message: string;
	suggestion?: string;
}

export interface AnalysisResult {
	analyzer: string;
	score: number;
	label: string;
	findings: AnalysisFinding[];
	passed: boolean;
}

export interface AnalysisReport {
	job_slug?: string;
	generated_at: string;
	overall_score: number;
	results: AnalysisResult[];
	summary: string;
}

// ── Profile ────────────────────────────────────────────────────────────────

export interface Profile {
	schema_version?: string;
	name: string;
	title?: string;
	email?: string;
	phone?: string;
	linkedin?: string;
	github?: string;
	website?: string;
	location?: string;
	languages?: string[];
}

// ── Experience ─────────────────────────────────────────────────────────────

export interface Bullet {
	id: string;
	text: string;
	tags?: string[];
	metrics?: boolean;
}

export interface Position {
	id: string;
	company: string;
	title: string;
	start_date: string;
	end_date?: string | null;
	is_current?: boolean;
	location?: string;
	bullets: Bullet[];
	tags?: string[];
	priority?: number;
}

export interface Experience {
	schema_version?: string;
	positions: Position[];
}

// ── Skills ─────────────────────────────────────────────────────────────────

export interface SkillCategory {
	id: string;
	label: string;
	items: string[];
	priority?: number;
}

export interface Skills {
	schema_version?: string;
	categories: SkillCategory[];
	exploring?: SkillCategory[];
}

// ── Education ──────────────────────────────────────────────────────────────

export interface EducationEntry {
	id: string;
	institution: string;
	degree: string;
	field?: string;
	start_date?: string;
	end_date?: string | null;
	gpa?: number;
	honors?: string[];
	notes?: string;
}

export interface Education {
	schema_version?: string;
	entries: EducationEntry[];
}

// ── Projects ───────────────────────────────────────────────────────────────

export interface Project {
	id: string;
	name: string;
	description: string;
	url?: string;
	technologies?: string[];
	highlights?: string[];
	start_date?: string;
	end_date?: string | null;
}

export interface Projects {
	schema_version?: string;
	projects: Project[];
}

// ── Certifications ─────────────────────────────────────────────────────────

export interface Certification {
	id: string;
	name: string;
	issuer: string;
	date?: string;
	expiry?: string | null;
	url?: string;
	credential_id?: string;
}

export interface Certifications {
	schema_version?: string;
	certifications: Certification[];
}

// ── Job Description ────────────────────────────────────────────────────────

export interface JobDescription {
	slug: string;
	title: string;
	company: string;
	description: string;
	requirements?: string[];
	nice_to_have?: string[];
	language?: string;
	saved_date?: string;
	notes?: string;
}

// ── Meta / Config ──────────────────────────────────────────────────────────

export interface EngineConfig {
	mode?: 'local' | 'cloud';
	url?: string | null;
	port?: number;
}

export interface AIConfig {
	provider?: string;
	model?: string;
	base_url?: string | null;
	temperature?: number;
	enabled?: boolean;
}

export interface StyleConfig {
	tone?: string;
	max_pages?: number;
	bullet_style?: string;
	avoid_tool_names_in_bullets?: boolean;
}

export interface Meta {
	schema_version?: string;
	default_locale?: string;
	default_template?: string;
	default_format?: string;
	engine?: EngineConfig;
	ai?: AIConfig;
	style?: StyleConfig;
}

// ── Templates ──────────────────────────────────────────────────────────────

export interface TemplateInfo {
	name: string;
	label: string;
	description?: string;
	supported_formats?: string[];
	ats_friendly?: boolean;
	max_pages?: number;
	author?: string;
	version?: string;
}

// ── Generic section data ───────────────────────────────────────────────────

export type SectionData =
	| Profile
	| Experience
	| Skills
	| Education
	| Projects
	| Certifications
	| Meta
	| Record<string, unknown>;
