package client

import "encoding/json"

// BuildRequest holds parameters for POST /api/build (sent as query params).
type BuildRequest struct {
	Template string `json:"template"`
	Format   string `json:"format"`
	JobSlug  string `json:"job_slug,omitempty"`
	Locale   string `json:"locale,omitempty"`
	Analyze  bool   `json:"analyze"`
}

// BuildResponse is returned by POST /api/build.
type BuildResponse struct {
	OutputPath  string          `json:"output_path"`
	Format      string          `json:"format"`
	Template    string          `json:"template"`
	GeneratedAt string          `json:"generated_at"`
	Analysis    *AnalysisReport `json:"analysis,omitempty"`
}

// TailorRequest is sent as JSON body to POST /api/tailor.
// The engine only supports job_slug and ai — job_file/model are CLI-only flags
// that the user would handle by saving a job first.
type TailorRequest struct {
	JobSlug string `json:"job_slug"`
	AI      bool   `json:"ai"`
}

// TailorResponse is returned by POST /api/tailor.
type TailorResponse struct {
	JobSlug         string   `json:"job_slug"`
	TailoredSummary string   `json:"tailored_summary"`
	MissingKeywords []string `json:"missing_keywords"`
	Suggestions     []string `json:"suggestions"`
}

// AnalyzeRequest is sent as JSON body to POST /api/analyze.
type AnalyzeRequest struct {
	JobSlug string `json:"job_slug,omitempty"`
}

// AnalysisReport mirrors the engine's AnalysisReport model.
// Returned by POST /api/analyze and GET /api/analyze/{job_slug},
// and embedded in BuildResponse.Analysis.
type AnalysisReport struct {
	GeneratedAt      string           `json:"generated_at"`
	OverallScore     float64          `json:"overall_score"`
	OverallLabel     string           `json:"overall_label"`
	Results          []AnalysisResult `json:"results"`
	TotalFindings    int              `json:"total_findings"`
	CriticalFindings int              `json:"critical_findings"`
}

// AnalysisResult is one analyzer's result within an AnalysisReport.
type AnalysisResult struct {
	Analyzer string            `json:"analyzer"`
	Score    float64           `json:"score"`
	MaxScore float64           `json:"max_score"`
	Label    string            `json:"label"`
	Findings []Finding         `json:"findings"`
	Metadata map[string]interface{} `json:"metadata"`
}

// Finding is a single issue or observation from an analyzer.
type Finding struct {
	Message    string `json:"message"`
	Severity   string `json:"severity"`
	Field      string `json:"field,omitempty"`
	Suggestion string `json:"suggestion,omitempty"`
}

// TemplateInfo represents a template returned by GET /api/templates.
type TemplateInfo struct {
	Name             string   `json:"name"`
	Description      string   `json:"description"`
	SupportedFormats []string `json:"supported_formats"`
	ATSFriendly      bool     `json:"ats_friendly"`
}

// JobInfo represents a saved job description.
type JobInfo struct {
	Slug        string `json:"slug"`
	Title       string `json:"title"`
	Company     string `json:"company"`
	Description string `json:"description"`
}

// Config mirrors the engine Meta configuration.
type Config struct {
	DefaultTemplate string       `json:"default_template"`
	DefaultFormat   string       `json:"default_format"`
	DefaultLocale   string       `json:"default_locale"`
	AI              AIConfig     `json:"ai"`
	Engine          EngineConfig `json:"engine"`
}

// AIConfig holds AI provider settings.
type AIConfig struct {
	Provider    string  `json:"provider"`
	Model       string  `json:"model"`
	Enabled     bool    `json:"enabled"`
	Temperature float64 `json:"temperature"`
}

// EngineConfig holds engine connection settings.
type EngineConfig struct {
	Mode string `json:"mode"`
	URL  string `json:"url"`
	Port int    `json:"port"`
}

// SSEEvent is a single Server-Sent Event received from a streaming endpoint.
type SSEEvent struct {
	Type string
	Data string
}

// rawMessage is used internally for section data passthrough.
type rawMessage = json.RawMessage
