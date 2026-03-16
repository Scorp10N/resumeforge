package screens

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/resumeforge/resumeforge/client"
)

// analysisResultMsg carries the result of a general analysis fetch.
type analysisResultMsg struct {
	resp *client.AnalysisReport
	err  error
}

// AnalysisModel is the analysis report screen.
type AnalysisModel struct {
	client   *client.Client
	width    int
	height   int
	spinner  spinner.Model
	viewport viewport.Model
	loading  bool
	err      string
	result   *client.AnalysisReport
}

// NewAnalysis creates a new AnalysisModel.
func NewAnalysis(c *client.Client) AnalysisModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	vp := viewport.New(80, 20)
	return AnalysisModel{
		client:   c,
		spinner:  s,
		viewport: vp,
		loading:  true,
	}
}

// SetSize updates the screen dimensions and resizes the viewport.
func (m AnalysisModel) SetSize(w, h int) AnalysisModel {
	m.width = w
	m.height = h
	m.viewport.Width = w
	m.viewport.Height = h - 8
	return m
}

// Init triggers a general (no-job) analysis fetch.
func (m AnalysisModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, fetchAnalysis(m.client))
}

func (m AnalysisModel) Update(msg tea.Msg) (AnalysisModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case spinner.TickMsg:
		if m.loading {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			cmds = append(cmds, cmd)
		}

	case analysisResultMsg:
		m.loading = false
		if msg.err != nil {
			m.err = fmt.Sprintf("Analysis failed: %v", msg.err)
		} else {
			m.err = ""
			m.result = msg.resp
			m.viewport.SetContent(buildReportText(msg.resp))
			m.viewport.GotoTop()
		}

	default:
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m AnalysisModel) View() string {
	var b strings.Builder

	b.WriteString(sectionStyle.Render("Analysis Report"))
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(bodyStyle.Render(m.spinner.View() + "  Running analysis…"))
		b.WriteString("\n")
		return b.String()
	}

	if m.err != "" {
		b.WriteString(errStyle.Render(m.err))
		b.WriteString("\n")
		return b.String()
	}

	if m.result == nil {
		b.WriteString(bodyStyle.Render("No analysis data."))
		return b.String()
	}

	// Score bars from Results.
	if len(m.result.Results) > 0 {
		b.WriteString(sectionStyle.Render("Scores"))
		b.WriteString("\n")
		for _, r := range m.result.Results {
			ratio := 0.0
			if r.MaxScore > 0 {
				ratio = r.Score / r.MaxScore
			}
			b.WriteString(bodyStyle.Render(renderScoreBar(r.Analyzer, ratio)))
			b.WriteString("\n")
		}
		b.WriteString("\n")
	}

	// Full report in scrollable viewport.
	b.WriteString(sectionStyle.Render("Report"))
	b.WriteString("\n")
	b.WriteString(m.viewport.View())
	b.WriteString("\n")
	b.WriteString(bodyStyle.Render(fmt.Sprintf("%d%%", int(m.viewport.ScrollPercent()*100)) + " ↑/↓ or j/k: scroll"))

	return b.String()
}

// fetchAnalysis runs a general (no-job-slug) analysis.
func fetchAnalysis(c *client.Client) tea.Cmd {
	return func() tea.Msg {
		resp, err := c.Analyze(client.AnalyzeRequest{})
		return analysisResultMsg{resp: resp, err: err}
	}
}

// buildReportText renders an AnalysisReport as a text string for the viewport.
func buildReportText(r *client.AnalysisReport) string {
	if r == nil {
		return ""
	}
	var b strings.Builder
	b.WriteString(fmt.Sprintf("Overall: %s (%.0f%%)\n", r.OverallLabel, r.OverallScore*100))
	b.WriteString(fmt.Sprintf("Findings: %d total, %d critical\n\n", r.TotalFindings, r.CriticalFindings))
	for _, res := range r.Results {
		b.WriteString(fmt.Sprintf("▸ %-25s %s\n", res.Analyzer+":", res.Label))
		for _, f := range res.Findings {
			prefix := "  • "
			if f.Severity == "critical" || f.Severity == "high" {
				prefix = "  ✗ "
			}
			b.WriteString(prefix + f.Message + "\n")
			if f.Suggestion != "" {
				b.WriteString("    → " + f.Suggestion + "\n")
			}
		}
		b.WriteString("\n")
	}
	return b.String()
}
