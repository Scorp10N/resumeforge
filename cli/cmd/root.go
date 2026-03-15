// Package cmd contains all Cobra command definitions for the resumeforge CLI.
package cmd

import (
	"fmt"
	"os"

	"github.com/resumeforge/resumeforge/client"
	"github.com/spf13/cobra"
)

var (
	engineURL  string
	enginePort int
	engineDir  string
)

// engineClient returns a configured client and ensures the engine is running.
// Commands that need the engine call this helper.
func engineClient(cmd *cobra.Command) (*client.Client, error) {
	c := client.New(engineURL)
	if err := c.EnsureEngine(enginePort, engineDir); err != nil {
		return nil, fmt.Errorf("start engine: %w", err)
	}
	return c, nil
}

// rootCmd is the base command for the resumeforge CLI.
var rootCmd = &cobra.Command{
	Use:   "resumeforge",
	Short: "ResumeForge — automated resume building and tailoring",
	Long: `ResumeForge is an open-source resume automation platform.

It separates resume content from presentation, enabling rapid building,
tailoring, and exporting of resumes for specific roles.`,
}

// Execute runs the root command. Called from main.go.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().StringVar(&engineURL, "engine", "http://localhost:8080", "Engine base URL")
	rootCmd.PersistentFlags().IntVar(&enginePort, "port", 8080, "Local engine port (used when auto-spawning)")
	rootCmd.PersistentFlags().StringVar(&engineDir, "engine-dir", "", "Path to the engine/ directory (default: ../engine relative to binary)")

	rootCmd.AddCommand(buildCmd)
	rootCmd.AddCommand(tailorCmd)
	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(templatesCmd)
	rootCmd.AddCommand(dataCmd)
	rootCmd.AddCommand(configCmd)
	rootCmd.AddCommand(tuiCmd)
}
