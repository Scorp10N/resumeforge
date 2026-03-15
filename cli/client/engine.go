package client

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// EnsureEngine checks whether the engine is already running on the configured
// port. If not, it spawns `uv run uvicorn resumeforge.api.app:app --port <port>`
// inside engineDir and waits up to 15 seconds for it to become healthy.
//
// engineDir should be the absolute path to the engine/ directory. If empty,
// EnsureEngine resolves it as "../engine" relative to the CLI binary.
func (c *Client) EnsureEngine(port int, engineDir string) error {
	// Fast path: engine already up.
	if err := c.Health(); err == nil {
		return nil
	}

	dir, err := resolveEngineDir(engineDir)
	if err != nil {
		return fmt.Errorf("locate engine directory: %w", err)
	}

	if err := spawnEngine(dir, port); err != nil {
		return fmt.Errorf("spawn engine: %w", err)
	}

	return c.waitHealthy(15 * time.Second)
}

// resolveEngineDir returns engineDir if non-empty; otherwise it computes
// ../engine relative to the running executable.
func resolveEngineDir(engineDir string) (string, error) {
	if engineDir != "" {
		return engineDir, nil
	}
	exe, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("get executable path: %w", err)
	}
	return filepath.Join(filepath.Dir(exe), "..", "engine"), nil
}

// spawnEngine launches the engine as a background process using uv.
func spawnEngine(engineDir string, port int) error {
	cmd := exec.Command(
		"uv", "run", "uvicorn",
		"resumeforge.api.app:app",
		"--port", fmt.Sprintf("%d", port),
	)
	cmd.Dir = engineDir

	// Inherit stderr so the user sees startup errors; suppress stdout noise.
	cmd.Stderr = os.Stderr

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start engine process: %w", err)
	}

	// Detach: we do not wait on the process. The engine runs independently until
	// the OS reclaims it or the user shuts it down.
	go func() {
		_ = cmd.Wait()
	}()

	return nil
}

// waitHealthy polls Health() until it succeeds or the timeout is reached.
func (c *Client) waitHealthy(timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	ticker := time.NewTicker(300 * time.Millisecond)
	defer ticker.Stop()

	for {
		if err := c.Health(); err == nil {
			return nil
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("engine did not become healthy within %s", timeout)
		}
		<-ticker.C
	}
}
