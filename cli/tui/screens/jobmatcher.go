package screens

import (
	"fmt"
	"sort"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/resumeforge/resumeforge/client"
)

// jobsLoadedMsg carries the list of saved jobs.
type jobsLoadedMsg struct {
	jobs []client.JobInfo
	err  error
}

// matchResultMsg carries analysis results for the selected job.
type matchResultMsg struct {
	resp *client.AnalysisReport
	err  error
}

var (
	scoreBarFull  = lipgloss.NewStyle().Foreground(lipgloss.Color("120"))
	scoreBarEmpty = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	scoreLabel    = lipgloss.NewStyle().Foreground(lipgloss.Color("250")).Width(28)
)

// JobMatcherModel is the job matcher screen.
type JobMatcherModel struct {
	client    *client.Client
	width     int
	height    int
	input     textinput.Model
	jobs      []client.JobInfo
	loading   bool
	analyzing bool
	spinner   spinner.Model
	result    *client.AnalysisReport
	err       string
}

// NewJobMatcher creates a new JobMatcherModel.
func NewJobMatcher(c *client.Client) JobMatcherModel {
	ti := textinput.New()
	ti.Placeholder = "job slug (e.g. bank-appsec)"
	ti.Focus()
	ti.CharLimit = 64

	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	return JobMatcherModel{
		client:  c,
		input:   ti,
		spinner: s,
		loading: true,
	}
}

// SetSize updates dimensions.
func (m JobMatcherModel) SetSize(w, h int) JobMatcherModel {
	m.width = w
	m.height = h
	return m
}

func (m JobMatcherModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, fetchJobs(m.client))
}

func (m JobMatcherModel) Update(msg tea.Msg) (JobMatcherModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case spinner.TickMsg:
		if m.loading || m.analyzing {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			cmds = append(cmds, cmd)
		}

	case jobsLoadedMsg:
		m.loading = false
		if msg.err != nil {
			m.err = fmt.Sprintf("Could not load jobs: %v", msg.err)
		} else {
			m.jobs = msg.jobs
		}

	case matchResultMsg:
		m.analyzing = false
		if msg.err != nil {
			m.err = fmt.Sprintf("Analysis failed: %v", msg.err)
		} else {
			m.result = msg.resp
			m.err = ""
		}

	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			slug := strings.TrimSpace(m.input.Value())
			if slug == "" {
				m.err = "Enter a job slug first."
				return m, nil
			}
			m.analyzing = true
			m.result = nil
			m.err = ""
			cmds = append(cmds, m.spinner.Tick, runAnalysis(m.client, slug))
		default:
			var cmd tea.Cmd
			m.input, cmd = m.input.Update(msg)
			cmds = append(cmds, cmd)
		}

	default:
		var cmd tea.Cmd
		m.input, cmd = m.input.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m JobMatcherModel) View() string {
	var b strings.Builder

	b.WriteString(sectionStyle.Render("Job Matcher"))
	b.WriteString("\n\n")

	// Job slug input.
	b.WriteString(bodyStyle.Render("Job slug: " + m.input.View()))
	b.WriteString("\n")
	b.WriteString(helpStyle.Render("enter: analyze against this job"))
	b.WriteString("\n\n")

	// Saved jobs list.
	if m.loading {
		b.WriteString(bodyStyle.Render(m.spinner.View() + "  Loading saved jobs…"))
		b.WriteString("\n")
	} else if len(m.jobs) > 0 {
		b.WriteString(sectionStyle.Render("Saved Jobs"))
		b.WriteString("\n")
		for _, j := range m.jobs {
			b.WriteString(bodyStyle.Render(fmt.Sprintf("  %-20s %s — %s", j.Slug, j.Title, j.Company)))
			b.WriteString("\n")
		}
		b.WriteString("\n")
	}

	if m.err != "" {
		b.WriteString(errStyle.Render(m.err))
		b.WriteString("\n")
	}

	if m.analyzing {
		b.WriteString(bodyStyle.Render(m.spinner.View() + "  Analyzing…"))
		b.WriteString("\n")
		return b.String()
	}

	if m.result != nil {
		b.WriteString(sectionStyle.Render("Results"))
		b.WriteString("\n")

		if len(m.result.Scores) > 0 {
			keys := make([]string, 0, len(m.result.Scores))
			for k := range m.result.Scores {
				keys = append(keys, k)
			}
			sort.Strings(keys)

			for _, k := range keys {
				score := m.result.Scores[k]
				b.WriteString(bodyStyle.Render(renderScoreBar(k, score)))
				b.WriteString("\n")
			}
			b.WriteString("\n")
		}

		if m.result.Report != "" {
			// Show first 20 lines of the report.
			lines := strings.SplitN(m.result.Report, "\n", 21)
			if len(lines) > 20 {
				lines = append(lines[:20], "  … (use resumeforge analyze for full report)")
			}
			b.WriteString(sectionStyle.Render("Report Preview"))
			b.WriteString("\n")
			b.WriteString(bodyStyle.Render(strings.Join(lines, "\n")))
			b.WriteString("\n")
		}
	}

	return b.String()
}

// renderScoreBar renders a visual bar for a score 0.0–1.0.
func renderScoreBar(label string, score float64) string {
	const barWidth = 20
	filled := int(score * barWidth)
	if filled > barWidth {
		filled = barWidth
	}
	bar := scoreBarFull.Render(strings.Repeat("█", filled)) +
		scoreBarEmpty.Render(strings.Repeat("░", barWidth-filled))
	pct := fmt.Sprintf("%.0f%%", score*100)
	return scoreLabel.Render(label+":") + " " + bar + "  " + pct
}

func fetchJobs(c *client.Client) tea.Cmd {
	return func() tea.Msg {
		jobs, err := c.ListJobs()
		return jobsLoadedMsg{jobs: jobs, err: err}
	}
}

func runAnalysis(c *client.Client, jobSlug string) tea.Cmd {
	return func() tea.Msg {
		// Try cached first.
		resp, err := c.GetAnalysis(jobSlug)
		if err != nil {
			resp, err = c.Analyze(client.AnalyzeRequest{JobSlug: jobSlug})
		}
		return matchResultMsg{resp: resp, err: err}
	}
}
