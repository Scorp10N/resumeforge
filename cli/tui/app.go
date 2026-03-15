// Package tui implements the Bubble Tea TUI for ResumeForge.
package tui

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/resumeforge/resumeforge/client"
	"github.com/resumeforge/resumeforge/tui/screens"
)

// Screen identifies which screen is currently active.
type Screen int

const (
	ScreenDashboard Screen = iota
	ScreenEditor
	ScreenJobMatcher
	ScreenAnalysis
)

// tabLabel maps each screen to its tab label.
var tabLabels = []string{"Dashboard", "Editor", "Job Matcher", "Analysis"}

// styles used across the app shell.
var (
	tabStyle = lipgloss.NewStyle().
			Padding(0, 2).
			Foreground(lipgloss.Color("240"))

	activeTabStyle = lipgloss.NewStyle().
			Padding(0, 2).
			Bold(true).
			Foreground(lipgloss.Color("205"))

	tabBarStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderBottom(true).
			BorderForeground(lipgloss.Color("240"))

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240")).
			Padding(0, 1)
)

// Model is the top-level Bubble Tea model.
type Model struct {
	client    *client.Client
	screen    Screen
	width     int
	height    int
	dashboard screens.DashboardModel
	editor    screens.EditorModel
	jobMatch  screens.JobMatcherModel
	analysis  screens.AnalysisModel
}

// New creates the top-level TUI model.
func New(c *client.Client) Model {
	return Model{
		client:    c,
		screen:    ScreenDashboard,
		dashboard: screens.NewDashboard(c),
		editor:    screens.NewEditor(c),
		jobMatch:  screens.NewJobMatcher(c),
		analysis:  screens.NewAnalysis(c),
	}
}

// Run starts the TUI program.
func Run(c *client.Client) error {
	m := New(c)
	p := tea.NewProgram(m, tea.WithAltScreen())
	_, err := p.Run()
	return err
}

func (m Model) Init() tea.Cmd {
	return m.dashboard.Init()
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		innerH := m.height - 4 // tab bar + help line
		m.dashboard = m.dashboard.SetSize(m.width, innerH)
		m.editor = m.editor.SetSize(m.width, innerH)
		m.jobMatch = m.jobMatch.SetSize(m.width, innerH)
		m.analysis = m.analysis.SetSize(m.width, innerH)
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			if m.screen == ScreenDashboard {
				return m, tea.Quit
			}
			// q navigates back to dashboard from sub-screens.
			m.screen = ScreenDashboard
			return m, m.dashboard.Init()
		case "1":
			m.screen = ScreenDashboard
			return m, m.dashboard.Init()
		case "2":
			m.screen = ScreenEditor
			return m, m.editor.Init()
		case "3":
			m.screen = ScreenJobMatcher
			return m, m.jobMatch.Init()
		case "4":
			m.screen = ScreenAnalysis
			return m, m.analysis.Init()
		case "tab":
			m.screen = (m.screen + 1) % Screen(len(tabLabels))
			return m, m.initCurrentScreen()
		}
	}

	// Delegate remaining messages to the active screen.
	var cmd tea.Cmd
	switch m.screen {
	case ScreenDashboard:
		m.dashboard, cmd = m.dashboard.Update(msg)
	case ScreenEditor:
		m.editor, cmd = m.editor.Update(msg)
	case ScreenJobMatcher:
		m.jobMatch, cmd = m.jobMatch.Update(msg)
	case ScreenAnalysis:
		m.analysis, cmd = m.analysis.Update(msg)
	}
	return m, cmd
}

func (m Model) View() string {
	// Tab bar.
	tabs := make([]string, len(tabLabels))
	for i, label := range tabLabels {
		num := fmt.Sprintf("%d:", i+1)
		if Screen(i) == m.screen {
			tabs[i] = activeTabStyle.Render(num + label)
		} else {
			tabs[i] = tabStyle.Render(num + label)
		}
	}
	tabBar := tabBarStyle.Width(m.width).Render(lipgloss.JoinHorizontal(lipgloss.Top, tabs...))

	// Active screen content.
	var content string
	switch m.screen {
	case ScreenDashboard:
		content = m.dashboard.View()
	case ScreenEditor:
		content = m.editor.View()
	case ScreenJobMatcher:
		content = m.jobMatch.View()
	case ScreenAnalysis:
		content = m.analysis.View()
	}

	// Help footer.
	help := helpStyle.Render("tab: next screen  1-4: jump  q: back/quit  ctrl+c: quit")

	return lipgloss.JoinVertical(lipgloss.Left, tabBar, content, help)
}

func (m Model) initCurrentScreen() tea.Cmd {
	switch m.screen {
	case ScreenDashboard:
		return m.dashboard.Init()
	case ScreenEditor:
		return m.editor.Init()
	case ScreenJobMatcher:
		return m.jobMatch.Init()
	case ScreenAnalysis:
		return m.analysis.Init()
	}
	return nil
}
