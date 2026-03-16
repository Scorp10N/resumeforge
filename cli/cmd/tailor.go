package cmd

import (
	"fmt"

	"github.com/resumeforge/resumeforge/client"
	"github.com/spf13/cobra"
)

var (
	tailorJob     string
	tailorJobFile string
	tailorAI      bool
	tailorModel   string
	tailorStream  bool
)

var tailorCmd = &cobra.Command{
	Use:   "tailor",
	Short: "Tailor your resume to a specific job description",
	Long: `Tailor your resume content to a specific job description using AI or rule-based matching.

Examples:
  resumeforge tailor --job bank-appsec --ai
  resumeforge tailor --job-file ./description.txt --ai --model claude-opus-4-20250514`,
	RunE: runTailor,
}

func init() {
	tailorCmd.Flags().StringVar(&tailorJob, "job", "", "Job slug from saved jobs")
	tailorCmd.Flags().StringVar(&tailorJobFile, "job-file", "", "Path to a job description text file")
	tailorCmd.Flags().BoolVar(&tailorAI, "ai", false, "Use AI for tailoring")
	tailorCmd.Flags().StringVar(&tailorModel, "model", "", "AI model override (e.g. claude-opus-4-20250514)")
	tailorCmd.Flags().BoolVar(&tailorStream, "stream", false, "Stream SSE progress to stdout")
}

func runTailor(cmd *cobra.Command, args []string) error {
	if tailorJob == "" && tailorJobFile == "" {
		return fmt.Errorf("either --job or --job-file is required")
	}

	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	req := client.TailorRequest{
		JobSlug: tailorJob,
		AI:      tailorAI,
	}

	if tailorStream {
		return streamTailor(c, req)
	}

	resp, err := c.Tailor(req)
	if err != nil {
		return fmt.Errorf("tailor failed: %w", err)
	}

	fmt.Printf("Tailored for: %s\n", resp.JobSlug)
	if resp.TailoredSummary != "" {
		fmt.Printf("\nSuggested summary:\n%s\n", resp.TailoredSummary)
	}
	if len(resp.MissingKeywords) > 0 {
		fmt.Printf("\nMissing keywords: %s\n", joinStrings(resp.MissingKeywords))
	}
	for _, s := range resp.Suggestions {
		fmt.Printf("• %s\n", s)
	}
	return nil
}

func streamTailor(c *client.Client, req client.TailorRequest) error {
	ch, err := c.StreamTailor(req)
	if err != nil {
		return fmt.Errorf("start tailor stream: %w", err)
	}
	for event := range ch {
		switch event.Type {
		case "done":
			fmt.Printf("\nDone: %s\n", event.Data)
		case "error":
			return fmt.Errorf("tailor error: %s", event.Data)
		default:
			fmt.Printf("[%s] %s\n", event.Type, event.Data)
		}
	}
	return nil
}
