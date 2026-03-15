package screens

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/resumeforge/resumeforge/client"
)

// editorTabStyle and editorActiveTabStyle are local to the editor screen.
// The screens package cannot import the tui package (circular dependency).
var (
	editorTabStyle = lipgloss.NewStyle().
			Padding(0, 1).
			Foreground(lipgloss.Color("240"))

	editorActiveTabStyle = lipgloss.NewStyle().
				Padding(0, 1).
				Bold(true).
				Foreground(lipgloss.Color("39")).
				Underline(true)

	editorHelpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240")).
			Padding(0, 1)
)

var validSections = []string{
	"profile", "experience", "skills", "education", "projects", "certifications",
}

// sectionLoadedMsg carries a fetched section payload.
type sectionLoadedMsg struct {
	section string
	data    json.RawMessage
	err     error
}

// EditorModel is the data section viewer screen.
type EditorModel struct {
	client   *client.Client
	width    int
	height   int
	sections []string
	selected int
	loading  bool
	spinner  spinner.Model
	viewport viewport.Model
	err      string
}

// NewEditor creates a new EditorModel.
func NewEditor(c *client.Client) EditorModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("39"))

	vp := viewport.New(80, 20)
	return EditorModel{
		client:   c,
		sections: validSections,
		selected: 0,
		spinner:  s,
		viewport: vp,
	}
}

// SetSize updates dimensions.
func (m EditorModel) SetSize(w, h int) EditorModel {
	m.width = w
	m.height = h
	m.viewport.Width = w
	m.viewport.Height = h - 6
	return m
}

func (m EditorModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, loadSection(m.client, m.sections[m.selected]))
}

func (m EditorModel) Update(msg tea.Msg) (EditorModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case spinner.TickMsg:
		if m.loading {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			cmds = append(cmds, cmd)
		}

	case sectionLoadedMsg:
		m.loading = false
		m.err = ""
		if msg.err != nil {
			m.err = fmt.Sprintf("Error loading %q: %v", msg.section, msg.err)
		} else {
			pretty, err := json.MarshalIndent(json.RawMessage(msg.data), "", "  ")
			if err != nil {
				m.err = fmt.Sprintf("Parse error: %v", err)
			} else {
				m.viewport.SetContent(string(pretty))
				m.viewport.GotoTop()
			}
		}

	case tea.KeyMsg:
		switch msg.String() {
		case "left", "h":
			if m.selected > 0 {
				m.selected--
				m.loading = true
				cmds = append(cmds, m.spinner.Tick, loadSection(m.client, m.sections[m.selected]))
			}
		case "right", "l":
			if m.selected < len(m.sections)-1 {
				m.selected++
				m.loading = true
				cmds = append(cmds, m.spinner.Tick, loadSection(m.client, m.sections[m.selected]))
			}
		default:
			var cmd tea.Cmd
			m.viewport, cmd = m.viewport.Update(msg)
			cmds = append(cmds, cmd)
		}

	default:
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m EditorModel) View() string {
	var b strings.Builder

	b.WriteString(sectionStyle.Render("Data Editor"))
	b.WriteString("\n")

	tabs := make([]string, len(m.sections))
	for i, s := range m.sections {
		if i == m.selected {
			tabs[i] = editorActiveTabStyle.Render(s)
		} else {
			tabs[i] = editorTabStyle.Render(s)
		}
	}
	b.WriteString(bodyStyle.Render(lipgloss.JoinHorizontal(lipgloss.Top, tabs...)))
	b.WriteString("\n\n")

	if m.err != "" {
		b.WriteString(errStyle.Render(m.err))
		b.WriteString("\n")
		return b.String()
	}

	if m.loading {
		b.WriteString(bodyStyle.Render(m.spinner.View() + "  Loading " + m.sections[m.selected] + "…"))
		b.WriteString("\n")
		return b.String()
	}

	b.WriteString(m.viewport.View())
	b.WriteString("\n")
	b.WriteString(editorHelpStyle.Render("←/→: switch section  ↑/↓ or j/k: scroll  to edit: resumeforge data edit <section>"))

	return b.String()
}

func loadSection(c *client.Client, section string) tea.Cmd {
	return func() tea.Msg {
		data, err := c.GetSection(section)
		return sectionLoadedMsg{section: section, data: data, err: err}
	}
}
