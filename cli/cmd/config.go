package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "View and modify ResumeForge configuration",
}

var configGetCmd = &cobra.Command{
	Use:   "get [key]",
	Short: "Get configuration (all or a single key)",
	Long: `Print the current configuration as JSON.

Examples:
  resumeforge config get
  resumeforge config get ai.model`,
	Args: cobra.MaximumNArgs(1),
	RunE: runConfigGet,
}

var configSetCmd = &cobra.Command{
	Use:   "set <key> <value>",
	Short: "Set a configuration key",
	Long: `Set a configuration value using dot-notation key.

Examples:
  resumeforge config set ai.model gpt-4o
  resumeforge config set ai.enabled true
  resumeforge config set engine.url https://cloud.resumeforge.io`,
	Args: cobra.ExactArgs(2),
	RunE: runConfigSet,
}

func init() {
	configCmd.AddCommand(configGetCmd)
	configCmd.AddCommand(configSetCmd)
}

func runConfigGet(cmd *cobra.Command, args []string) error {
	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	cfg, err := c.GetConfig()
	if err != nil {
		return fmt.Errorf("get config: %w", err)
	}

	if len(args) == 1 {
		// Extract the requested key from the marshalled config.
		raw, err := json.Marshal(cfg)
		if err != nil {
			return fmt.Errorf("marshal config: %w", err)
		}
		val, err := extractDotKey(raw, args[0])
		if err != nil {
			return err
		}
		fmt.Fprintln(cmd.OutOrStdout(), val)
		return nil
	}

	enc := json.NewEncoder(cmd.OutOrStdout())
	enc.SetIndent("", "  ")
	return enc.Encode(cfg)
}

func runConfigSet(cmd *cobra.Command, args []string) error {
	key, value := args[0], args[1]

	c, err := engineClient(cmd)
	if err != nil {
		return err
	}

	if err := c.SetConfig(key, value); err != nil {
		return fmt.Errorf("set config %q = %q: %w", key, value, err)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Config updated: %s = %s\n", key, value)
	return nil
}

// extractDotKey reads a dot-notation key from a JSON blob and returns the
// value as a string. E.g. key "ai.model" from {"ai":{"model":"gpt-4o"}} → "gpt-4o".
func extractDotKey(data []byte, key string) (string, error) {
	var m interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		return "", fmt.Errorf("parse config: %w", err)
	}

	cur := m
	parts := splitDotKey(key)
	for _, part := range parts {
		switch v := cur.(type) {
		case map[string]interface{}:
			val, ok := v[part]
			if !ok {
				return "", fmt.Errorf("key %q not found in config", key)
			}
			cur = val
		default:
			return "", fmt.Errorf("key %q not found in config", key)
		}
	}

	switch v := cur.(type) {
	case string:
		return v, nil
	default:
		b, err := json.Marshal(v)
		if err != nil {
			return "", fmt.Errorf("marshal value: %w", err)
		}
		return string(b), nil
	}
}

func splitDotKey(key string) []string {
	var parts []string
	start := 0
	for i := 0; i < len(key); i++ {
		if key[i] == '.' {
			parts = append(parts, key[start:i])
			start = i + 1
		}
	}
	parts = append(parts, key[start:])
	return parts
}
