package cmd

import (
	"github.com/resumeforge/resumeforge/tui"
	"github.com/spf13/cobra"
)

var tuiCmd = &cobra.Command{
	Use:   "tui",
	Short: "Launch the interactive TUI",
	Long:  `Launch the Bubble Tea TUI for interactive resume editing and building.`,
	RunE:  runTUI,
}

func runTUI(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}
	return tui.Run(c)
}
