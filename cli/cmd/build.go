package cmd

import (
	"fmt"

	"github.com/resumeforge/resumeforge/client"
	"github.com/spf13/cobra"
)

var (
	buildTemplate string
	buildFormat   string
	buildJob      string
	buildLang     string
	buildAnalyze  bool
	buildStream   bool
)

var buildCmd = &cobra.Command{
	Use:   "build",
	Short: "Build a resume from your data and a template",
	Long: `Build a resume from your stored data using the specified template and format.

Examples:
  resumeforge build --template classic --format pdf
  resumeforge build --template modern --format docx --job bank-appsec --lang he
  resumeforge build --format pdf --analyze`,
	RunE: runBuild,
}

func init() {
	buildCmd.Flags().StringVar(&buildTemplate, "template", "classic", "Template to use")
	buildCmd.Flags().StringVar(&buildFormat, "format", "pdf", "Output format: pdf, docx, md")
	buildCmd.Flags().StringVar(&buildJob, "job", "", "Job slug to tailor the build")
	buildCmd.Flags().StringVar(&buildLang, "lang", "", "Language/locale override (e.g. 'he', 'en')")
	buildCmd.Flags().BoolVar(&buildAnalyze, "analyze", false, "Run analysis after build")
	buildCmd.Flags().BoolVar(&buildStream, "stream", false, "Stream SSE progress to stdout")
}

func runBuild(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	req := client.BuildRequest{
		Template: buildTemplate,
		Format:   buildFormat,
		JobSlug:  buildJob,
		Lang:     buildLang,
		Analyze:  buildAnalyze,
	}

	if buildStream {
		return streamBuild(c, req)
	}

	resp, err := c.Build(req)
	if err != nil {
		return fmt.Errorf("build failed: %w", err)
	}

	fmt.Printf("Build complete: %s\n", resp.OutputPath)
	if resp.Analysis != nil {
		fmt.Printf("\nAnalysis: %s  (%d findings, %d critical)\n",
			resp.Analysis.OverallLabel,
			resp.Analysis.TotalFindings,
			resp.Analysis.CriticalFindings,
		)
	}
	return nil
}

func streamBuild(c *client.Client, req client.BuildRequest) error {
	ch, err := c.StreamBuild(req)
	if err != nil {
		return fmt.Errorf("start build stream: %w", err)
	}
	for event := range ch {
		switch event.Type {
		case "done":
			fmt.Printf("\nDone: %s\n", event.Data)
		case "error":
			return fmt.Errorf("build error: %s", event.Data)
		default:
			fmt.Printf("[%s] %s\n", event.Type, event.Data)
		}
	}
	return nil
}
