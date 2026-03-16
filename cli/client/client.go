// Package client provides a typed HTTP client for the ResumeForge engine API.
// All engine communication in the CLI and TUI must go through this package.
package client

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// Client is a typed HTTP client for the ResumeForge engine REST API.
type Client struct {
	BaseURL    string
	HTTPClient *http.Client
}

// New returns a Client targeting baseURL (e.g. "http://localhost:8080").
func New(baseURL string) *Client {
	return &Client{
		BaseURL: strings.TrimRight(baseURL, "/"),
		HTTPClient: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

// Health calls GET /health and returns an error if the engine is unreachable or unhealthy.
func (c *Client) Health() error {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/health")
	if err != nil {
		return fmt.Errorf("engine unreachable: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("engine health check failed: HTTP %d", resp.StatusCode)
	}
	return nil
}

// Build calls POST /api/build with query parameters and returns the build response.
// The engine's build endpoint uses Query params, not a JSON body.
func (c *Client) Build(req BuildRequest) (*BuildResponse, error) {
	var resp BuildResponse
	if err := c.postQuery("/api/build", buildQueryParams(req), &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

// StreamBuild calls GET /api/build/stream with query parameters and returns a channel of SSE events.
// The channel is closed when the stream ends or an error occurs.
func (c *Client) StreamBuild(req BuildRequest) (<-chan SSEEvent, error) {
	url := c.BaseURL + "/api/build/stream?" + buildQueryParams(req).Encode()
	httpReq, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("create stream request: %w", err)
	}
	httpReq.Header.Set("Accept", "text/event-stream")
	return c.streamSSE(httpReq)
}

// Tailor calls POST /api/tailor with a JSON body and returns the tailor response.
func (c *Client) Tailor(req TailorRequest) (*TailorResponse, error) {
	var resp TailorResponse
	if err := c.postJSON("/api/tailor", req, &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

// StreamTailor calls GET /api/tailor/stream with query parameters and returns a channel of SSE events.
func (c *Client) StreamTailor(req TailorRequest) (<-chan SSEEvent, error) {
	params := urlValues{}
	params.Set("job_slug", req.JobSlug)
	if req.AI {
		params.Set("ai", "true")
	}
	url := c.BaseURL + "/api/tailor/stream?" + params.Encode()
	httpReq, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("create stream request: %w", err)
	}
	httpReq.Header.Set("Accept", "text/event-stream")
	return c.streamSSE(httpReq)
}

// Analyze calls POST /api/analyze and returns the analysis report.
func (c *Client) Analyze(req AnalyzeRequest) (*AnalysisReport, error) {
	var resp AnalysisReport
	if err := c.postJSON("/api/analyze", req, &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

// GetAnalysis calls GET /api/analyze/{jobSlug} and returns the cached analysis report.
func (c *Client) GetAnalysis(jobSlug string) (*AnalysisReport, error) {
	var resp AnalysisReport
	if err := c.getJSON("/api/analyze/"+jobSlug, &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

// GetSection calls GET /api/data/{section} and returns the raw JSON for the section.
func (c *Client) GetSection(section string) (json.RawMessage, error) {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/api/data/" + section)
	if err != nil {
		return nil, fmt.Errorf("get section %q: %w", section, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return nil, err
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read section body: %w", err)
	}
	return json.RawMessage(data), nil
}

// PutSection calls PUT /api/data/{section} with the raw JSON data.
func (c *Client) PutSection(section string, data json.RawMessage) error {
	req, err := http.NewRequest(http.MethodPut, c.BaseURL+"/api/data/"+section, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("create put request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("put section %q: %w", section, err)
	}
	defer resp.Body.Close()
	return checkStatus(resp)
}

// ExportData calls GET /api/data/export and writes the zip to outputPath.
func (c *Client) ExportData(outputPath string) error {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/api/data/export")
	if err != nil {
		return fmt.Errorf("export data: %w", err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return err
	}
	f, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("create output file %q: %w", outputPath, err)
	}
	defer f.Close()
	if _, err := io.Copy(f, resp.Body); err != nil {
		return fmt.Errorf("write export zip: %w", err)
	}
	return nil
}

// ImportData calls POST /api/data/import with the zip file at inputPath.
func (c *Client) ImportData(inputPath string) error {
	f, err := os.Open(inputPath)
	if err != nil {
		return fmt.Errorf("open import file %q: %w", inputPath, err)
	}
	defer f.Close()

	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	fw, err := mw.CreateFormFile("file", filepath.Base(inputPath))
	if err != nil {
		return fmt.Errorf("create form file: %w", err)
	}
	if _, err := io.Copy(fw, f); err != nil {
		return fmt.Errorf("copy import file: %w", err)
	}
	mw.Close()

	resp, err := c.HTTPClient.Post(c.BaseURL+"/api/data/import", mw.FormDataContentType(), &buf)
	if err != nil {
		return fmt.Errorf("import data: %w", err)
	}
	defer resp.Body.Close()
	return checkStatus(resp)
}

// ListTemplates calls GET /api/templates and returns the list of templates.
func (c *Client) ListTemplates() ([]TemplateInfo, error) {
	var templates []TemplateInfo
	if err := c.getJSON("/api/templates", &templates); err != nil {
		return nil, err
	}
	return templates, nil
}

// PreviewTemplate calls GET /api/templates/{name}/preview and returns the raw bytes.
func (c *Client) PreviewTemplate(name, format string) ([]byte, error) {
	url := fmt.Sprintf("%s/api/templates/%s/preview", c.BaseURL, name)
	if format != "" {
		url += "?format=" + format
	}
	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("preview template %q: %w", name, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return nil, err
	}
	return io.ReadAll(resp.Body)
}

// ListJobs calls GET /api/jobs and returns the list of saved jobs.
func (c *Client) ListJobs() ([]JobInfo, error) {
	var jobs []JobInfo
	if err := c.getJSON("/api/jobs", &jobs); err != nil {
		return nil, err
	}
	return jobs, nil
}

// GetJob calls GET /api/jobs/{slug} and returns the job info.
func (c *Client) GetJob(slug string) (*JobInfo, error) {
	var job JobInfo
	if err := c.getJSON("/api/jobs/"+slug, &job); err != nil {
		return nil, err
	}
	return &job, nil
}

// SaveJob calls POST /api/jobs with the job info.
func (c *Client) SaveJob(job JobInfo) error {
	return c.postJSON("/api/jobs", job, nil)
}

// DeleteJob calls DELETE /api/jobs/{slug}.
func (c *Client) DeleteJob(slug string) error {
	req, err := http.NewRequest(http.MethodDelete, c.BaseURL+"/api/jobs/"+slug, nil)
	if err != nil {
		return fmt.Errorf("create delete request: %w", err)
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("delete job %q: %w", slug, err)
	}
	defer resp.Body.Close()
	return checkStatus(resp)
}

// GetConfig calls GET /api/config and returns the current config.
func (c *Client) GetConfig() (*Config, error) {
	var cfg Config
	if err := c.getJSON("/api/config", &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

// SetConfig calls PATCH /api/config with a single dot-notation key and value.
// The key is converted to a nested JSON patch object.
func (c *Client) SetConfig(key, value string) error {
	patch := dotKeyToPatch(key, value)
	return c.patchJSON("/api/config", patch, nil)
}

// --- internal helpers ---

func (c *Client) getJSON(path string, out interface{}) error {
	resp, err := c.HTTPClient.Get(c.BaseURL + path)
	if err != nil {
		return fmt.Errorf("GET %s: %w", path, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}
	return nil
}

func (c *Client) postJSON(path string, in interface{}, out interface{}) error {
	body, err := json.Marshal(in)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}
	resp, err := c.HTTPClient.Post(c.BaseURL+path, "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("POST %s: %w", path, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}
	return nil
}

func (c *Client) patchJSON(path string, in interface{}, out interface{}) error {
	body, err := json.Marshal(in)
	if err != nil {
		return fmt.Errorf("marshal patch request: %w", err)
	}
	req, err := http.NewRequest(http.MethodPatch, c.BaseURL+path, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create patch request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("PATCH %s: %w", path, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}
	return nil
}

// streamSSE executes the request and returns a channel of SSEEvents.
// The channel is closed when the stream ends. The HTTP client for SSE does not
// use the default timeout so long-running streams are not cut off.
func (c *Client) streamSSE(req *http.Request) (<-chan SSEEvent, error) {
	// Use a client without timeout for streaming.
	sseClient := &http.Client{}
	resp, err := sseClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("start SSE stream: %w", err)
	}
	if err := checkStatus(resp); err != nil {
		resp.Body.Close()
		return nil, err
	}

	ch := make(chan SSEEvent, 16)
	go func() {
		defer close(ch)
		defer resp.Body.Close()

		scanner := bufio.NewScanner(resp.Body)
		var event SSEEvent
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				// Blank line signals dispatch of the event.
				if event.Data != "" || event.Type != "" {
					ch <- event
					event = SSEEvent{}
				}
				continue
			}
			if strings.HasPrefix(line, "event:") {
				event.Type = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
			} else if strings.HasPrefix(line, "data:") {
				event.Data = strings.TrimSpace(strings.TrimPrefix(line, "data:"))
			}
		}
	}()

	return ch, nil
}

// checkStatus returns an error if the HTTP response status is not 2xx.
func checkStatus(resp *http.Response) error {
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return nil
	}
	body, _ := io.ReadAll(resp.Body)
	msg := strings.TrimSpace(string(body))
	if msg == "" {
		msg = resp.Status
	}
	return fmt.Errorf("engine returned HTTP %d: %s", resp.StatusCode, msg)
}

// urlValues is a named type for URL query parameters with Set and Encode helpers.
type urlValues map[string][]string

func (v urlValues) Set(key, val string) { v[key] = []string{val} }
func (v urlValues) Encode() string {
	if len(v) == 0 {
		return ""
	}
	// Simple encode: key=val&key2=val2 (no special chars in our params).
	parts := make([]string, 0, len(v))
	for k, vals := range v {
		for _, val := range vals {
			parts = append(parts, k+"="+val)
		}
	}
	// Sort for determinism.
	for i := 1; i < len(parts); i++ {
		for j := i; j > 0 && parts[j] < parts[j-1]; j-- {
			parts[j], parts[j-1] = parts[j-1], parts[j]
		}
	}
	result := ""
	for i, p := range parts {
		if i > 0 {
			result += "&"
		}
		result += p
	}
	return result
}

// buildQueryParams converts a BuildRequest into URL query parameters.
func buildQueryParams(req BuildRequest) urlValues {
	params := urlValues{}
	params.Set("template", req.Template)
	params.Set("format", req.Format)
	if req.JobSlug != "" {
		params.Set("job_slug", req.JobSlug)
	}
	if req.Locale != "" {
		params.Set("locale", req.Locale)
	}
	if req.Analyze {
		params.Set("analyze", "true")
	} else {
		params.Set("analyze", "false")
	}
	return params
}

// postQuery sends a POST request to path with query parameters (no body) and decodes the response.
func (c *Client) postQuery(path string, params urlValues, out interface{}) error {
	url := c.BaseURL + path
	if len(params) > 0 {
		url += "?" + params.Encode()
	}
	resp, err := c.HTTPClient.Post(url, "application/json", nil)
	if err != nil {
		return fmt.Errorf("POST %s: %w", path, err)
	}
	defer resp.Body.Close()
	if err := checkStatus(resp); err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}
	return nil
}

// dotKeyToPatch converts a dot-notation key like "ai.model" and value "gpt-4o"
// into a nested map suitable for JSON PATCH: {"ai": {"model": "gpt-4o"}}.
func dotKeyToPatch(key, value string) map[string]interface{} {
	parts := strings.Split(key, ".")
	result := make(map[string]interface{})
	cur := result
	for i, part := range parts {
		if i == len(parts)-1 {
			// At the leaf: attempt to decode value as JSON bool/number first.
			cur[part] = coerceValue(value)
		} else {
			next := make(map[string]interface{})
			cur[part] = next
			cur = next
		}
	}
	return result
}

// coerceValue attempts to parse value as a JSON bool or number; falls back to string.
func coerceValue(v string) interface{} {
	switch v {
	case "true":
		return true
	case "false":
		return false
	}
	var num json.Number
	if err := json.Unmarshal([]byte(v), &num); err == nil {
		// Try int first, then float.
		if i, err := num.Int64(); err == nil {
			return i
		}
		if f, err := num.Float64(); err == nil {
			return f
		}
	}
	return v
}
