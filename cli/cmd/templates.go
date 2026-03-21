package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/resumeforge/resumeforge/client"
	"github.com/spf13/cobra"
)

var templatesCmd = &cobra.Command{
	Use:   "templates",
	Short: "Manage and preview resume templates",
}

var templatesListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all available templates",
	RunE:  runTemplatesList,
}

var (
	previewFormat string
	previewOutput string
)

var templatesPreviewCmd = &cobra.Command{
	Use:   "preview <name>",
	Short: "Preview a template",
	Long: `Download a preview render of the given template.

Examples:
  resumeforge templates preview classic --format pdf
  resumeforge templates preview modern --format pdf --output modern.pdf`,
	Args: cobra.ExactArgs(1),
	RunE: runTemplatesPreview,
}

func init() {
	templatesCmd.AddCommand(templatesListCmd)
	templatesCmd.AddCommand(templatesPreviewCmd)

	templatesPreviewCmd.Flags().StringVar(&previewFormat, "format", "pdf", "Preview format: pdf, docx, md")
	templatesPreviewCmd.Flags().StringVar(&previewOutput, "output", "", "Output file path (default: <name>-preview.<format>)")
}

func runTemplatesList(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	templates, err := c.ListTemplates()
	if err != nil {
		return fmt.Errorf("list templates: %w", err)
	}

	if len(templates) == 0 {
		fmt.Fprintln(cmd.OutOrStdout(), "No templates found.")
		return nil
	}

	for _, t := range templates {
		ats := ""
		if t.ATSFriendly {
			ats = " [ATS-friendly]"
		}
		fmt.Fprintf(cmd.OutOrStdout(), "  %-15s %s%s\n", t.Name, t.Description, ats)
		fmt.Fprintf(cmd.OutOrStdout(), "               formats: %v\n", t.SupportedFormats)
	}
	return nil
}

func runTemplatesPreview(cmd *cobra.Command, args []string) error {
	name := args[0]

	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	data, err := c.PreviewTemplate(name, previewFormat)
	if err != nil {
		return fmt.Errorf("preview template %q: %w", name, err)
	}

	outPath := previewOutput
	if outPath == "" {
		outPath = fmt.Sprintf("%s-preview.%s", name, previewFormat)
	}

	// Ensure parent directory exists.
	if dir := filepath.Dir(outPath); dir != "." {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("create output directory: %w", err)
		}
	}

	if err := os.WriteFile(outPath, data, 0644); err != nil {
		return fmt.Errorf("write preview file: %w", err)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Preview saved to: %s\n", outPath)
	return nil
}

// listTemplatesForTesting returns templates using the provided client — used in tests.
func listTemplatesForTesting(c *client.Client) ([]client.TemplateInfo, error) {
	return c.ListTemplates()
}
