// Package screens contains individual Bubble Tea screen models.
package screens

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/resumeforge/resumeforge/client"
)

// templatesLoadedMsg carries the template list fetched from the engine.
type templatesLoadedMsg struct {
	templates []client.TemplateInfo
	err       error
}

// buildDoneMsg carries the result of a build triggered from the dashboard.
type buildDoneMsg struct {
	resp *client.BuildResponse
	err  error
}

// DashboardModel is the dashboard screen model.
type DashboardModel struct {
	client    *client.Client
	width     int
	height    int
	templates []client.TemplateInfo
	loading   bool
	spinner   spinner.Model
	lastBuild string
	status    string
	err       string
}

var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("205")).
			Padding(1, 2)

	sectionStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("39")).
			Padding(0, 2)

	bodyStyle = lipgloss.NewStyle().
			Padding(0, 4)

	statusStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("120")).
			Padding(0, 2)

	errStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("196")).
			Padding(0, 2)

	// helpStyle, tabStyle, activeTabStyle are shared across all screens in
	// this package (jobmatcher, analysis). Defined here in the package's
	// "base" file.
	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240")).
			Padding(0, 1)

	tabStyle = lipgloss.NewStyle().
			Padding(0, 2).
			Foreground(lipgloss.Color("240"))

	activeTabStyle = lipgloss.NewStyle().
			Padding(0, 2).
			Bold(true).
			Foreground(lipgloss.Color("205"))
)

// NewDashboard creates a new DashboardModel.
func NewDashboard(c *client.Client) DashboardModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))
	return DashboardModel{
		client:  c,
		spinner: s,
		loading: true,
	}
}

// SetSize updates the screen dimensions.
func (m DashboardModel) SetSize(w, h int) DashboardModel {
	m.width = w
	m.height = h
	return m
}

func (m DashboardModel) Init() tea.Cmd {
	return tea.Batch(
		m.spinner.Tick,
		fetchTemplates(m.client),
	)
}

func (m DashboardModel) Update(msg tea.Msg) (DashboardModel, tea.Cmd) {
	switch msg := msg.(type) {
	case spinner.TickMsg:
		if m.loading {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			return m, cmd
		}

	case templatesLoadedMsg:
		m.loading = false
		m.err = ""
		if msg.err != nil {
			m.err = fmt.Sprintf("Could not load templates: %v", msg.err)
		} else {
			m.templates = msg.templates
		}

	case buildDoneMsg:
		m.loading = false
		if msg.err != nil {
			m.err = fmt.Sprintf("Build failed: %v", msg.err)
		} else {
			m.lastBuild = msg.resp.OutputPath
			m.status = fmt.Sprintf("Built: %s", msg.resp.OutputPath)
		}

	case tea.KeyMsg:
		switch msg.String() {
		case "b":
			m.loading = true
			m.status = "Building resume…"
			m.err = ""
			return m, tea.Batch(m.spinner.Tick, triggerBuild(m.client))
		}
	}
	return m, nil
}

func (m DashboardModel) View() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("ResumeForge"))
	b.WriteString("\n")

	if m.loading {
		b.WriteString(bodyStyle.Render(m.spinner.View() + "  Loading…"))
		b.WriteString("\n")
	}

	if m.err != "" {
		b.WriteString(errStyle.Render(m.err))
		b.WriteString("\n")
	}

	if m.status != "" {
		b.WriteString(statusStyle.Render(m.status))
		b.WriteString("\n")
	}

	// Templates section.
	if len(m.templates) > 0 {
		b.WriteString(sectionStyle.Render("Templates"))
		b.WriteString("\n")
		for _, t := range m.templates {
			ats := ""
			if t.ATSFriendly {
				ats = " [ATS]"
			}
			line := fmt.Sprintf("%-15s %s%s  (%s)", t.Name, t.Description, ats, strings.Join(t.SupportedFormats, ", "))
			b.WriteString(bodyStyle.Render(line))
			b.WriteString("\n")
		}
		b.WriteString("\n")
	}

	// Quick actions.
	b.WriteString(sectionStyle.Render("Quick Actions"))
	b.WriteString("\n")
	actions := []string{
		"b  — build resume (classic, pdf)",
		"2  — open Editor to view/edit data sections",
		"3  — open Job Matcher to score resume against a job",
		"4  — open Analysis to see full report",
	}
	for _, a := range actions {
		b.WriteString(bodyStyle.Render(a))
		b.WriteString("\n")
	}

	if m.lastBuild != "" {
		b.WriteString("\n")
		b.WriteString(sectionStyle.Render("Last Build"))
		b.WriteString("\n")
		b.WriteString(bodyStyle.Render(m.lastBuild))
		b.WriteString("\n")
	}

	return b.String()
}

func fetchTemplates(c *client.Client) tea.Cmd {
	return func() tea.Msg {
		templates, err := c.ListTemplates()
		return templatesLoadedMsg{templates: templates, err: err}
	}
}

func triggerBuild(c *client.Client) tea.Cmd {
	return func() tea.Msg {
		resp, err := c.Build(client.BuildRequest{
			Template: "classic",
			Format:   "pdf",
		})
		return buildDoneMsg{resp: resp, err: err}
	}
}
