package client_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/resumeforge/resumeforge/client"
)

// newTestServer creates an httptest.Server and a Client pointing at it.
func newTestServer(handler http.Handler) (*httptest.Server, *client.Client) {
	srv := httptest.NewServer(handler)
	c := client.New(srv.URL)
	return srv, c
}

func TestHealth_OK(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			http.NotFound(w, r)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	if err := c.Health(); err != nil {
		t.Fatalf("Health() returned unexpected error: %v", err)
	}
}

func TestHealth_Error(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "not ready", http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	if err := c.Health(); err == nil {
		t.Fatal("Health() expected error for non-200 response, got nil")
	}
}

func TestBuild(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/api/build" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.BuildResponse{
			OutputPath:      "/output/resume.pdf",
			AnalysisSummary: "ATS: 85%",
		})
	}))
	defer srv.Close()

	req := client.BuildRequest{Template: "classic", Format: "pdf", Analyze: true}
	resp, err := c.Build(req)
	if err != nil {
		t.Fatalf("Build() error: %v", err)
	}
	if resp.OutputPath != "/output/resume.pdf" {
		t.Errorf("OutputPath = %q, want %q", resp.OutputPath, "/output/resume.pdf")
	}
	if resp.AnalysisSummary != "ATS: 85%" {
		t.Errorf("AnalysisSummary = %q, want %q", resp.AnalysisSummary, "ATS: 85%")
	}
}

func TestBuild_EngineError(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "template not found", http.StatusNotFound)
	}))
	defer srv.Close()

	_, err := c.Build(client.BuildRequest{Template: "missing"})
	if err == nil {
		t.Fatal("Build() expected error for 404, got nil")
	}
}

func TestTailor(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/api/tailor" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.TailorResponse{Message: "Resume tailored successfully"})
	}))
	defer srv.Close()

	resp, err := c.Tailor(client.TailorRequest{JobSlug: "bank-appsec", AI: true})
	if err != nil {
		t.Fatalf("Tailor() error: %v", err)
	}
	if resp.Message != "Resume tailored successfully" {
		t.Errorf("Message = %q", resp.Message)
	}
}

func TestAnalyze(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/analyze" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.AnalyzeResponse{
			Report: "All good",
			Scores: map[string]float64{"ats": 0.85, "readability": 0.90},
		})
	}))
	defer srv.Close()

	resp, err := c.Analyze(client.AnalyzeRequest{JobSlug: "bank-appsec"})
	if err != nil {
		t.Fatalf("Analyze() error: %v", err)
	}
	if resp.Scores["ats"] != 0.85 {
		t.Errorf("ats score = %.2f, want 0.85", resp.Scores["ats"])
	}
}

func TestGetAnalysis(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/analyze/bank-appsec" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.AnalyzeResponse{Report: "cached"})
	}))
	defer srv.Close()

	resp, err := c.GetAnalysis("bank-appsec")
	if err != nil {
		t.Fatalf("GetAnalysis() error: %v", err)
	}
	if resp.Report != "cached" {
		t.Errorf("Report = %q", resp.Report)
	}
}

func TestGetSection(t *testing.T) {
	payload := `{"schema_version":"1.0","positions":[]}`
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/data/experience" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(payload))
	}))
	defer srv.Close()

	raw, err := c.GetSection("experience")
	if err != nil {
		t.Fatalf("GetSection() error: %v", err)
	}
	if string(raw) != payload {
		t.Errorf("GetSection() = %s, want %s", raw, payload)
	}
}

func TestPutSection(t *testing.T) {
	var received []byte
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut || r.URL.Path != "/api/data/experience" {
			http.NotFound(w, r)
			return
		}
		received, _ = json.Marshal(struct{}{})
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()
	_ = received

	err := c.PutSection("experience", json.RawMessage(`{"positions":[]}`))
	if err != nil {
		t.Fatalf("PutSection() error: %v", err)
	}
}

func TestListTemplates(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/templates" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode([]client.TemplateInfo{
			{Name: "classic", Description: "Classic layout", Formats: []string{"pdf", "docx"}, ATSFriendly: true},
			{Name: "modern", Description: "Modern layout", Formats: []string{"pdf"}, ATSFriendly: false},
		})
	}))
	defer srv.Close()

	templates, err := c.ListTemplates()
	if err != nil {
		t.Fatalf("ListTemplates() error: %v", err)
	}
	if len(templates) != 2 {
		t.Fatalf("expected 2 templates, got %d", len(templates))
	}
	if templates[0].Name != "classic" {
		t.Errorf("templates[0].Name = %q, want %q", templates[0].Name, "classic")
	}
	if !templates[0].ATSFriendly {
		t.Error("expected classic to be ATS-friendly")
	}
}

func TestPreviewTemplate(t *testing.T) {
	pdfBytes := []byte("%PDF-1.4 fake")
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/templates/classic/preview" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/pdf")
		w.Write(pdfBytes)
	}))
	defer srv.Close()

	data, err := c.PreviewTemplate("classic", "pdf")
	if err != nil {
		t.Fatalf("PreviewTemplate() error: %v", err)
	}
	if string(data) != string(pdfBytes) {
		t.Errorf("unexpected preview data")
	}
}

func TestListJobs(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/jobs" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode([]client.JobInfo{
			{Slug: "bank-appsec", Title: "AppSec Engineer", Company: "Big Bank"},
		})
	}))
	defer srv.Close()

	jobs, err := c.ListJobs()
	if err != nil {
		t.Fatalf("ListJobs() error: %v", err)
	}
	if len(jobs) != 1 || jobs[0].Slug != "bank-appsec" {
		t.Errorf("unexpected jobs: %+v", jobs)
	}
}

func TestGetJob(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/jobs/bank-appsec" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.JobInfo{Slug: "bank-appsec", Title: "AppSec"})
	}))
	defer srv.Close()

	job, err := c.GetJob("bank-appsec")
	if err != nil {
		t.Fatalf("GetJob() error: %v", err)
	}
	if job.Slug != "bank-appsec" {
		t.Errorf("Slug = %q", job.Slug)
	}
}

func TestDeleteJob(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete || r.URL.Path != "/api/jobs/old-job" {
			http.NotFound(w, r)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	if err := c.DeleteJob("old-job"); err != nil {
		t.Fatalf("DeleteJob() error: %v", err)
	}
}

func TestGetConfig(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/config" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(client.Config{
			DefaultTemplate: "classic",
			DefaultFormat:   "pdf",
			AI:              client.AIConfig{Model: "gpt-4o", Enabled: false},
		})
	}))
	defer srv.Close()

	cfg, err := c.GetConfig()
	if err != nil {
		t.Fatalf("GetConfig() error: %v", err)
	}
	if cfg.DefaultTemplate != "classic" {
		t.Errorf("DefaultTemplate = %q", cfg.DefaultTemplate)
	}
	if cfg.AI.Model != "gpt-4o" {
		t.Errorf("AI.Model = %q", cfg.AI.Model)
	}
}

func TestSetConfig(t *testing.T) {
	var patchBody map[string]interface{}
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPatch || r.URL.Path != "/api/config" {
			http.NotFound(w, r)
			return
		}
		json.NewDecoder(r.Body).Decode(&patchBody)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	if err := c.SetConfig("ai.model", "claude-opus-4-20250514"); err != nil {
		t.Fatalf("SetConfig() error: %v", err)
	}

	// Verify the patch shape: {"ai": {"model": "claude-opus-4-20250514"}}
	ai, ok := patchBody["ai"].(map[string]interface{})
	if !ok {
		t.Fatalf("patch body missing 'ai' key, got: %v", patchBody)
	}
	if ai["model"] != "claude-opus-4-20250514" {
		t.Errorf("ai.model = %v, want claude-opus-4-20250514", ai["model"])
	}
}

func TestSetConfig_Bool(t *testing.T) {
	var patchBody map[string]interface{}
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewDecoder(r.Body).Decode(&patchBody)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	if err := c.SetConfig("ai.enabled", "true"); err != nil {
		t.Fatalf("SetConfig(bool) error: %v", err)
	}

	ai, ok := patchBody["ai"].(map[string]interface{})
	if !ok {
		t.Fatalf("patch body missing 'ai' key")
	}
	if ai["enabled"] != true {
		t.Errorf("ai.enabled = %v, want true", ai["enabled"])
	}
}

func TestStreamBuild(t *testing.T) {
	srv, c := newTestServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher, ok := w.(http.Flusher)
		if !ok {
			t.Error("response writer does not support flushing")
			return
		}
		w.Write([]byte("event: progress\ndata: building sections\n\n"))
		flusher.Flush()
		w.Write([]byte("event: done\ndata: /output/resume.pdf\n\n"))
		flusher.Flush()
	}))
	defer srv.Close()

	ch, err := c.StreamBuild(client.BuildRequest{Template: "classic", Format: "pdf"})
	if err != nil {
		t.Fatalf("StreamBuild() error: %v", err)
	}

	var events []client.SSEEvent
	for e := range ch {
		events = append(events, e)
	}

	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
	if events[0].Type != "progress" || events[0].Data != "building sections" {
		t.Errorf("event[0] = %+v", events[0])
	}
	if events[1].Type != "done" || events[1].Data != "/output/resume.pdf" {
		t.Errorf("event[1] = %+v", events[1])
	}
}
