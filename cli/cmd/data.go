package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"

	"github.com/spf13/cobra"
)

var dataCmd = &cobra.Command{
	Use:   "data",
	Short: "View and manage resume data sections",
}

var dataShowCmd = &cobra.Command{
	Use:   "show <section>",
	Short: "Show a data section as pretty-printed JSON",
	Long: `Print the raw JSON for a resume data section.

Examples:
  resumeforge data show experience
  resumeforge data show skills`,
	Args: cobra.ExactArgs(1),
	RunE: runDataShow,
}

var dataEditSectionFlag string

var dataEditCmd = &cobra.Command{
	Use:   "edit <section>",
	Short: "Open a data section in $EDITOR",
	Long: `Download a data section, open it in $EDITOR, and push changes back on save.

Examples:
  resumeforge data edit experience
  resumeforge data edit experience --section scorp-2025`,
	Args: cobra.ExactArgs(1),
	RunE: runDataEdit,
}

var dataExportOutput string

var dataExportCmd = &cobra.Command{
	Use:   "export",
	Short: "Export all data as a zip archive",
	Long: `Download all resume data as a zip backup archive.

Examples:
  resumeforge data export
  resumeforge data export --output backup.zip`,
	RunE: runDataExport,
}

var dataImportInput string

var dataImportCmd = &cobra.Command{
	Use:   "import",
	Short: "Import data from a zip archive",
	Long: `Upload a previously exported zip archive to restore data.

Examples:
  resumeforge data import --input backup.zip`,
	RunE: runDataImport,
}

func init() {
	dataCmd.AddCommand(dataShowCmd)
	dataCmd.AddCommand(dataEditCmd)
	dataCmd.AddCommand(dataExportCmd)
	dataCmd.AddCommand(dataImportCmd)

	dataEditCmd.Flags().StringVar(&dataEditSectionFlag, "section", "", "Sub-section ID to jump to (informational)")
	dataExportCmd.Flags().StringVar(&dataExportOutput, "output", "backup.zip", "Output zip file path")
	dataImportCmd.Flags().StringVar(&dataImportInput, "input", "", "Input zip file path")
	_ = dataImportCmd.MarkFlagRequired("input")
}

func runDataShow(cmd *cobra.Command, args []string) error {
	section := args[0]
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	raw, err := c.GetSection(section)
	if err != nil {
		return fmt.Errorf("get section %q: %w", section, err)
	}

	var pretty interface{}
	if err := json.Unmarshal(raw, &pretty); err != nil {
		// Not valid JSON — just print raw.
		fmt.Fprintln(cmd.OutOrStdout(), string(raw))
		return nil
	}

	enc := json.NewEncoder(cmd.OutOrStdout())
	enc.SetIndent("", "  ")
	return enc.Encode(pretty)
}

func runDataEdit(cmd *cobra.Command, args []string) error {
	section := args[0]
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	// Fetch current data.
	raw, err := c.GetSection(section)
	if err != nil {
		return fmt.Errorf("get section %q: %w", section, err)
	}

	// Pretty-print to temp file.
	var pretty interface{}
	if err := json.Unmarshal(raw, &pretty); err != nil {
		return fmt.Errorf("parse section JSON: %w", err)
	}
	formatted, err := json.MarshalIndent(pretty, "", "  ")
	if err != nil {
		return fmt.Errorf("format section JSON: %w", err)
	}

	tmpFile, err := os.CreateTemp("", fmt.Sprintf("resumeforge-%s-*.json", section))
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.Write(formatted); err != nil {
		tmpFile.Close()
		return fmt.Errorf("write temp file: %w", err)
	}
	tmpFile.Close()

	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vi"
	}

	editorCmd := exec.Command(editor, tmpFile.Name())
	editorCmd.Stdin = os.Stdin
	editorCmd.Stdout = os.Stdout
	editorCmd.Stderr = os.Stderr
	if err := editorCmd.Run(); err != nil {
		return fmt.Errorf("editor exited with error: %w", err)
	}

	// Read back the edited content.
	edited, err := os.ReadFile(tmpFile.Name())
	if err != nil {
		return fmt.Errorf("read edited file: %w", err)
	}

	// Validate JSON before sending.
	var validate interface{}
	if err := json.Unmarshal(edited, &validate); err != nil {
		return fmt.Errorf("edited file is not valid JSON: %w", err)
	}

	if err := c.PutSection(section, json.RawMessage(edited)); err != nil {
		return fmt.Errorf("save section %q: %w", section, err)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Section %q saved.\n", section)
	return nil
}

func runDataExport(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	if err := c.ExportData(dataExportOutput); err != nil {
		return fmt.Errorf("export data: %w", err)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Data exported to: %s\n", dataExportOutput)
	return nil
}

func runDataImport(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	if err := c.ImportData(dataImportInput); err != nil {
		return fmt.Errorf("import data: %w", err)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Data imported from: %s\n", dataImportInput)
	return nil
}
