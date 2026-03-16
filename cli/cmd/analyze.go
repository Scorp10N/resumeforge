package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/resumeforge/resumeforge/client"
	"github.com/spf13/cobra"
)

var (
	analyzeJob    string
	analyzeFormat string
)

var analyzeCmd = &cobra.Command{
	Use:   "analyze",
	Short: "Analyze your resume against a job description",
	Long: `Run the analysis suite against your resume, optionally targeting a saved job.

Examples:
  resumeforge analyze --job bank-appsec
  resumeforge analyze --format json`,
	RunE: runAnalyze,
}

func init() {
	analyzeCmd.Flags().StringVar(&analyzeJob, "job", "", "Job slug to analyze against")
	analyzeCmd.Flags().StringVar(&analyzeFormat, "format", "text", "Output format: text, json")
}

func runAnalyze(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	var resp *client.AnalysisReport

	if analyzeJob != "" {
		// Try cached analysis first.
		resp, err = c.GetAnalysis(analyzeJob)
		if err != nil {
			// Fall back to running a fresh analysis.
			resp, err = c.Analyze(client.AnalyzeRequest{JobSlug: analyzeJob})
			if err != nil {
				return fmt.Errorf("analyze failed: %w", err)
			}
		}
	} else {
		resp, err = c.Analyze(client.AnalyzeRequest{})
		if err != nil {
			return fmt.Errorf("analyze failed: %w", err)
		}
	}

	return printAnalysis(resp, analyzeFormat)
}

func printAnalysis(resp *client.AnalysisReport, format string) error {
	switch format {
	case "json":
		enc := json.NewEncoder(rootCmd.OutOrStdout())
		enc.SetIndent("", "  ")
		return enc.Encode(resp)
	default:
		fmt.Fprintf(rootCmd.OutOrStdout(), "Overall: %s\n", resp.OverallLabel)
		fmt.Fprintf(rootCmd.OutOrStdout(), "Findings: %d total, %d critical\n\n",
			resp.TotalFindings, resp.CriticalFindings)
		for _, result := range resp.Results {
			fmt.Fprintf(rootCmd.OutOrStdout(), "  %-25s %s\n", result.Analyzer+":", result.Label)
		}
		return nil
	}
}
