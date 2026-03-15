package client

import "encoding/json"

// BuildRequest is sent to POST /api/build.
type BuildRequest struct {
	Template string `json:"template"`
	Format   string `json:"format"`
	JobSlug  string `json:"job_slug,omitempty"`
	Lang     string `json:"lang,omitempty"`
	Analyze  bool   `json:"analyze"`
}

// BuildResponse is returned by POST /api/build.
type BuildResponse struct {
	OutputPath      string `json:"output_path"`
	AnalysisSummary string `json:"analysis_summary,omitempty"`
}

// TailorRequest is sent to POST /api/tailor.
type TailorRequest struct {
	JobSlug string `json:"job_slug,omitempty"`
	JobFile string `json:"job_file,omitempty"`
	AI      bool   `json:"ai"`
	Model   string `json:"model,omitempty"`
}

// TailorResponse is returned by POST /api/tailor.
type TailorResponse struct {
	Message string `json:"message"`
}

// AnalyzeRequest is sent to POST /api/analyze.
type AnalyzeRequest struct {
	JobSlug string `json:"job_slug,omitempty"`
}

// AnalyzeResponse is returned by POST /api/analyze and GET /api/analyze/{job_slug}.
type AnalyzeResponse struct {
	Report string             `json:"report"`
	Scores map[string]float64 `json:"scores"`
}

// TemplateInfo represents a template returned by GET /api/templates.
type TemplateInfo struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Formats     []string `json:"formats"`
	ATSFriendly bool     `json:"ats_friendly"`
}

// JobInfo represents a saved job description.
type JobInfo struct {
	Slug        string `json:"slug"`
	Title       string `json:"title"`
	Company     string `json:"company"`
	Description string `json:"description"`
}

// Config mirrors the engine configuration.
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

// SSEEvent is a single Server-Sent Event.
type SSEEvent struct {
	Type string
	Data string
}

// rawMessage is used internally for section data passthrough.
type rawMessage = json.RawMessage
