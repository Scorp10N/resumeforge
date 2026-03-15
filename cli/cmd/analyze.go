package cmd

import (
	"encoding/json"
	"fmt"
	"sort"

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

	var resp *client.AnalyzeResponse

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

func printAnalysis(resp *client.AnalyzeResponse, format string) error {
	switch format {
	case "json":
		enc := json.NewEncoder(rootCmd.OutOrStdout())
		enc.SetIndent("", "  ")
		return enc.Encode(resp)
	default:
		fmt.Fprintln(rootCmd.OutOrStdout(), resp.Report)
		if len(resp.Scores) > 0 {
			fmt.Fprintln(rootCmd.OutOrStdout(), "\nScores:")
			// Sort keys for deterministic output.
			keys := make([]string, 0, len(resp.Scores))
			for k := range resp.Scores {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			for _, k := range keys {
				fmt.Fprintf(rootCmd.OutOrStdout(), "  %-25s %.1f%%\n", k+":", resp.Scores[k]*100)
			}
		}
		return nil
	}
}
