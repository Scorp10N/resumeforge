package client_test

import (
	"encoding/json"
	"testing"

	"github.com/resumeforge/resumeforge/client"
)

func TestBuildRequest_Serialization(t *testing.T) {
	req := client.BuildRequest{
		Template: "modern",
		Format:   "docx",
		JobSlug:  "bank-appsec",
		Locale:   "he",
		Analyze:  true,
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var m map[string]interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}

	checks := map[string]interface{}{
		"template": "modern",
		"format":   "docx",
		"job_slug": "bank-appsec",
		"locale":   "he",
		"analyze":  true,
	}
	for k, want := range checks {
		if got := m[k]; got != want {
			t.Errorf("field %q = %v, want %v", k, got, want)
		}
	}
}

func TestTailorRequest_Serialization(t *testing.T) {
	req := client.TailorRequest{
		JobSlug: "bank-appsec",
		AI:      true,
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var m map[string]interface{}
	json.Unmarshal(data, &m)

	if m["job_slug"] != "bank-appsec" {
		t.Errorf("job_slug = %v", m["job_slug"])
	}
	if m["ai"] != true {
		t.Errorf("ai = %v", m["ai"])
	}
}

func TestConfig_RoundTrip(t *testing.T) {
	original := client.Config{
		DefaultTemplate: "classic",
		DefaultFormat:   "pdf",
		DefaultLocale:   "en",
		AI: client.AIConfig{
			Provider:    "openai",
			Model:       "gpt-4o",
			Enabled:     false,
			Temperature: 0.3,
		},
		Engine: client.EngineConfig{
			Mode: "local",
			Port: 8080,
		},
	}

	data, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded client.Config
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}

	if decoded.DefaultTemplate != original.DefaultTemplate {
		t.Errorf("DefaultTemplate mismatch")
	}
	if decoded.AI.Model != original.AI.Model {
		t.Errorf("AI.Model mismatch")
	}
	if decoded.Engine.Port != original.Engine.Port {
		t.Errorf("Engine.Port mismatch")
	}
}

func TestSSEEvent(t *testing.T) {
	e := client.SSEEvent{Type: "progress", Data: "50%"}
	if e.Type != "progress" {
		t.Errorf("Type = %q", e.Type)
	}
	if e.Data != "50%" {
		t.Errorf("Data = %q", e.Data)
	}
}
