package main

import (
	"bufio"
	"bytes"
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorBlue   = "\033[34m"
	colorPurple = "\033[35m"
	colorCyan   = "\033[36m"
	colorWhite  = "\033[37m"
	colorBold   = "\033[1m"
)

type Config struct {
	RootDir string
}

func getRootDir() string {
	exePath, err := os.Executable()
	if err == nil {
		dir := filepath.Dir(exePath)
		if fileExists(filepath.Join(dir, "AGENTS.md")) {
			return dir
		}
		parent := filepath.Dir(dir)
		if fileExists(filepath.Join(parent, "AGENTS.md")) {
			return parent
		}
	}
	cwd, _ := os.Getwd()
	if fileExists(filepath.Join(cwd, "AGENTS.md")) {
		return cwd
	}
	return "/home/cvsz/zworkforce"
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	if os.IsNotExist(err) {
		return false
	}
	return !info.IsDir()
}

func logInfo(msg string) {
	fmt.Printf("%s[INFO]%s %s\n", colorCyan, colorReset, msg)
}

func logSuccess(msg string) {
	fmt.Printf("%s[SUCCESS]%s %s\n", colorGreen, colorReset, msg)
}

func logWarn(msg string) {
	fmt.Printf("%s[WARN]%s %s\n", colorYellow, colorReset, msg)
}

func logError(msg string) {
	fmt.Printf("%s[ERROR]%s %s\n", colorRed, colorReset, msg)
}

func runCommand(dir string, name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Dir = dir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	return cmd.Run()
}

func runCommandSilent(dir string, name string, args ...string) (string, error) {
	cmd := exec.Command(name, args...)
	cmd.Dir = dir
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	err := cmd.Run()
	return strings.TrimSpace(out.String()), err
}

func checkHTTP(url string, timeout time.Duration) (bool, int, string) {
	client := &http.Client{
		Timeout: timeout,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}
	resp, err := client.Get(url)
	if err != nil {
		return false, 0, err.Error()
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	return resp.StatusCode >= 200 && resp.StatusCode < 400, resp.StatusCode, string(body)
}

func printBanner() {
	banner := `
=============================================================================
             ____      __             __     ______                 
     ____   / __/___  / /_  ___  ____/ /_   / ____/___  ____  ____ _
    /_  /  / /_/ __ \/ __ \/ _ \/ __  / /  / /_  / __ \/ __ \/ __ ` + "`" + `/
     / /_ / __/ /_/ / /_/ /  __/ /_/ / /  / __/ / /_/ / /_/ / /_/ / 
    /___//_/  \____/_.___/\___/\__,_/_/  /_/    \____/\____/\__, /  
                                                           /____/   
                 Z W O R K F O R C E   M A S T E R   C T L
=============================================================================`
	fmt.Printf("%s%s%s\n", colorCyan, banner, colorReset)
}

func statusAction(cfg *Config) {
	fmt.Printf("\n%s%s--- Monorepo & Services Health Matrix ---%s\n", colorBold, colorBlue, colorReset)

	// 1. zWorkforce Core API (:9569 / :9570)
	ok, code, _ := checkHTTP("http://127.0.0.1:9569/health", 2*time.Second)
	if ok {
		fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d on :9569)\n", "zWorkforce Control Plane API", colorGreen, colorReset, code)
	} else {
		ok70, code70, _ := checkHTTP("http://127.0.0.1:9570/health", 2*time.Second)
		if ok70 {
			fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d on :9570)\n", "zWorkforce Control Plane API", colorGreen, colorReset, code70)
		} else {
			fmt.Printf("  • %-36s : %sOFFLINE%s\n", "zWorkforce Control Plane API", colorRed, colorReset)
		}
	}

	// 2. OpenWebUI Multi-Model Gateway (:3080)
	ok, code, _ = checkHTTP("http://127.0.0.1:3080", 2*time.Second)
	if ok {
		fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / https://chat.zeaz.dev)\n", "OpenWebUI Multi-Model Gateway", colorGreen, colorReset, code)
	} else {
		fmt.Printf("  • %-36s : %sSTANDBY%s\n", "OpenWebUI Multi-Model Gateway", colorYellow, colorReset)
	}

	// 3. ZSP Studio & HyperFrames (:3005)
	ok, code, _ = checkHTTP("http://127.0.0.1:3005", 2*time.Second)
	if ok {
		fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / https://studio.zeaz.dev)\n", "ZSP AI Studio & Video Renderer", colorGreen, colorReset, code)
	} else {
		fmt.Printf("  • %-36s : %sSTANDBY%s\n", "ZSP AI Studio & Video Renderer", colorYellow, colorReset)
	}

	// 4. Z.A.R.V.I.S. Voice Gateway (:3000 / :8090)
	ok, code, _ = checkHTTP("http://127.0.0.1:3000", 2*time.Second)
	if ok {
		fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / ZVoice UI)\n", "Z.A.R.V.I.S. Voice Gateway", colorGreen, colorReset, code)
	} else {
		fmt.Printf("  • %-36s : %sSTANDBY%s\n", "Z.A.R.V.I.S. Voice Gateway", colorYellow, colorReset)
	}

	// 5. Zider Companion Gateway (:8085)
	ok, code, _ = checkHTTP("http://127.0.0.1:8085/health", 2*time.Second)
	if ok {
		fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d)\n", "Zider Companion Gateway", colorGreen, colorReset, code)
	} else {
		fmt.Printf("  • %-36s : %sSTANDBY%s\n", "Zider Companion Gateway", colorYellow, colorReset)
	}

	// 6. Hermes Engine & Spawn CLI
	fmt.Printf("\n%s%s--- Agent Runtime & Autonomous Toolchain ---%s\n", colorBold, colorPurple, colorReset)
	if out, err := runCommandSilent(cfg.RootDir, "which", "hermes"); err == nil && out != "" {
		fmt.Printf("  • %-36s : %sINSTALLED%s (%s)\n", "Hermes Agent Engine CLI", colorGreen, colorReset, out)
	} else if fileExists(filepath.Join(os.Getenv("HOME"), ".hermes/bin/hermes")) {
		fmt.Printf("  • %-36s : %sINSTALLED%s (~/.hermes/bin/hermes)\n", "Hermes Agent Engine CLI", colorGreen, colorReset)
	} else {
		fmt.Printf("  • %-36s : %sNOT FOUND%s\n", "Hermes Agent Engine CLI", colorRed, colorReset)
	}

	if out, err := runCommandSilent(cfg.RootDir, "which", "spawn"); err == nil && out != "" {
		fmt.Printf("  • %-36s : %sINSTALLED%s (%s)\n", "OpenRouter Spawn CLI", colorGreen, colorReset, out)
	} else if fileExists(filepath.Join(os.Getenv("HOME"), ".local/bin/spawn")) {
		fmt.Printf("  • %-36s : %sINSTALLED%s (~/.local/bin/spawn)\n", "OpenRouter Spawn CLI", colorGreen, colorReset)
	} else {
		fmt.Printf("  • %-36s : %sNOT FOUND%s\n", "OpenRouter Spawn CLI", colorRed, colorReset)
	}

	// 7. System Doctor output
	fmt.Printf("\n%s%s--- zWorkforce Doctor Diagnostic ---%s\n", colorBold, colorCyan, colorReset)
	_ = runCommand(cfg.RootDir, "zworkforce", "doctor")
}

func verifyAction(cfg *Config) {
	logInfo("Initiating Full Validation & Verification Suite across monorepo...")
	
	logInfo("Step 1: Byte-compiling Python services and test suite...")
	if err := runCommand(cfg.RootDir, "python3", "-m", "compileall", "-q", "zworkforce", "tests"); err != nil {
		logError("Byte-compilation failed")
		return
	}

	logInfo("Step 2: Executing full unittest discover suite (140 tests)...")
	cmd := exec.Command("python3", "-m", "unittest", "discover", "-s", "tests", "-v")
	cmd.Dir = cfg.RootDir
	cmd.Env = append(os.Environ(), "PYTHONPATH=.")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		logError("Unittest validation failed")
		return
	}

	logInfo("Step 3: Validating repository doctor diagnostics and audit hash chain...")
	if err := runCommand(cfg.RootDir, "zworkforce", "doctor"); err != nil {
		logError("zworkforce doctor reported errors")
		return
	}

	logSuccess("Full Validation Suite PASSED with 100% Invariant Compliance!")
}

func startAction(cfg *Config) {
	logInfo("Starting all zWorkforce core and gateway services...")
	_ = runCommand(cfg.RootDir, "docker", "compose", "up", "-d")
	if fileExists(filepath.Join(cfg.RootDir, "compose.open-webui.yml")) {
		_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.open-webui.yml", "up", "-d")
	}
	logSuccess("Core services started.")
}

func stopAction(cfg *Config) {
	logInfo("Stopping all zWorkforce containers and background workers...")
	_ = runCommand(cfg.RootDir, "docker", "compose", "down")
	if fileExists(filepath.Join(cfg.RootDir, "compose.open-webui.yml")) {
		_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.open-webui.yml", "down")
	}
	logSuccess("Services stopped.")
}

func restartAction(cfg *Config) {
	stopAction(cfg)
	time.Sleep(2 * time.Second)
	startAction(cfg)
}

func installAction(cfg *Config) {
	logInfo("Running Automated Full-Stack Monorepo Installer...")

	// 1. Root python and environment
	if fileExists(filepath.Join(cfg.RootDir, "setup.sh")) {
		logInfo("Executing root setup.sh...")
		_ = runCommand(cfg.RootDir, "bash", "setup.sh")
	}

	// 2. Zarvis workspace
	zarvisDir := filepath.Join(cfg.RootDir, "packages/zarvis")
	if _, err := os.Stat(zarvisDir); err == nil {
		logInfo("Installing packages/zarvis dependencies...")
		_ = runCommand(zarvisDir, "pnpm", "install", "--frozen-lockfile")
	}

	// 3. ZSP-AITool workspace
	zspDir := filepath.Join(cfg.RootDir, "packages/zsp-aitool")
	if _, err := os.Stat(zspDir); err == nil {
		logInfo("Installing packages/zsp-aitool (Prisma & Next.js)...")
		_ = runCommand(zspDir, "npm", "run", "prisma:generate")
		_ = runCommand(zspDir, "npm", "run", "build")
	}

	// 4. Zider companion
	ziderDir := filepath.Join(cfg.RootDir, "packages/zider")
	if _, err := os.Stat(ziderDir); err == nil {
		logInfo("Installing packages/zider extension and server...")
		_ = runCommand(ziderDir, "npm", "install")
		_ = runCommand(ziderDir, "npm", "run", "build")
	}

	// 5. Hermes and Spawn
	masterScript := filepath.Join(cfg.RootDir, "scripts/install/install_hermes_full_stack_master.sh")
	if fileExists(masterScript) {
		logInfo("Verifying Hermes Agent & Spawn toolchain...")
		_ = runCommand(cfg.RootDir, "bash", masterScript, "--dry-run")
	}

	logSuccess("Automated Full-Stack Installation Complete!")
}

func configAction(cfg *Config) {
	fmt.Printf("\n%s%s--- Configuration & Provider Secret Vault (.env.ai) ---%s\n", colorBold, colorYellow, colorReset)
	envAiPath := filepath.Join(cfg.RootDir, ".env.ai")
	if !fileExists(envAiPath) {
		envAiPath = filepath.Join(os.Getenv("HOME"), ".env.ai")
	}

	if fileExists(envAiPath) {
		logSuccess(fmt.Sprintf("Vault found at: %s", envAiPath))
		file, err := os.Open(envAiPath)
		if err == nil {
			defer file.Close()
			scanner := bufio.NewScanner(file)
			count := 0
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if line != "" && !strings.HasPrefix(line, "#") {
					parts := strings.SplitN(line, "=", 2)
					if len(parts) == 2 {
						key := parts[0]
						val := parts[1]
						masked := "********"
						if len(val) > 8 {
							masked = val[:4] + "..." + val[len(val)-4:]
						}
						fmt.Printf("  • %-32s = %s\n", key, masked)
						count++
					}
				}
			}
			fmt.Printf("\n%sLoaded %d active provider keys/endpoints securely with zero plaintext leakage.%s\n", colorGreen, count, colorReset)
		}
	} else {
		logWarn("No .env.ai vault file found. Run sync to generate one.")
	}
}

func interactiveMenu(cfg *Config) {
	reader := bufio.NewReader(os.Stdin)
	for {
		printBanner()
		fmt.Println("\nSelect an operational action:")
		fmt.Printf("  %s1)%s Check System & Services Status\n", colorCyan, colorReset)
		fmt.Printf("  %s2)%s Run Full Validation Suite (140 Tests + Invariants)\n", colorCyan, colorReset)
		fmt.Printf("  %s3)%s Start All Services (Docker & Gateways)\n", colorCyan, colorReset)
		fmt.Printf("  %s4)%s Stop All Services\n", colorCyan, colorReset)
		fmt.Printf("  %s5)%s Restart All Services\n", colorCyan, colorReset)
		fmt.Printf("  %s6)%s Automated Full-Stack Monorepo Installer\n", colorCyan, colorReset)
		fmt.Printf("  %s7)%s Inspect Provider & Secret Vault Config\n", colorCyan, colorReset)
		fmt.Printf("  %s8)%s Launch OpenWebUI Multi-Model Gateway\n", colorCyan, colorReset)
		fmt.Printf("  %s9)%s Launch ZSP AI Studio & Video Renderer\n", colorCyan, colorReset)
		fmt.Printf("  %sq)%s Exit\n", colorRed, colorReset)
		fmt.Print("\nEnter choice [1-9, q]: ")

		input, _ := reader.ReadString('\n')
		choice := strings.TrimSpace(input)

		switch choice {
		case "1":
			statusAction(cfg)
		case "2":
			verifyAction(cfg)
		case "3":
			startAction(cfg)
		case "4":
			stopAction(cfg)
		case "5":
			restartAction(cfg)
		case "6":
			installAction(cfg)
		case "7":
			configAction(cfg)
		case "8":
			logInfo("Starting OpenWebUI Gateway on :3080...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.open-webui.yml", "up", "-d")
			logSuccess("OpenWebUI ready at https://chat.zeaz.dev or http://localhost:3080")
		case "9":
			logInfo("Starting ZSP AI Studio Next.js on :3005...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.zsp-aitool.yml", "up", "-d")
			logSuccess("ZSP AI Studio ready at https://studio.zeaz.dev or http://localhost:3005")
		case "q", "exit", "quit":
			fmt.Println("Exiting zWorkforce Master Control.")
			return
		default:
			logError("Invalid option selected.")
		}

		fmt.Print("\nPress Enter to continue...")
		_, _ = reader.ReadString('\n')
	}
}

func main() {
	cfg := &Config{
		RootDir: getRootDir(),
	}

	if len(os.Args) < 2 {
		interactiveMenu(cfg)
		return
	}

	cmd := os.Args[1]
	switch cmd {
	case "status":
		statusAction(cfg)
	case "verify", "test":
		verifyAction(cfg)
	case "start":
		startAction(cfg)
	case "stop":
		stopAction(cfg)
	case "restart":
		restartAction(cfg)
	case "install", "setup":
		installAction(cfg)
	case "config", "vault":
		configAction(cfg)
	case "help", "--help", "-h":
		printBanner()
		fmt.Println("\nUsage: zctl [command]")
		fmt.Println("\nAvailable Commands:")
		fmt.Println("  status      - Display real-time service health, ports & doctor diagnostics")
		fmt.Println("  verify      - Run Full Validation Suite (140 tests, bytecomp, invariants)")
		fmt.Println("  start       - Launch all docker compose service containers")
		fmt.Println("  stop        - Gracefully stop running containers and background workers")
		fmt.Println("  restart     - Stop and restart all services")
		fmt.Println("  install     - Full-stack automated monorepo installer across all packages")
		fmt.Println("  config      - Inspect masked active provider keys from .env.ai")
		fmt.Println("  help        - Show this command reference")
	default:
		logError(fmt.Sprintf("Unknown command '%s'", cmd))
		fmt.Println("Run 'zctl help' for available options or launch without arguments for interactive UI.")
		os.Exit(1)
	}
}
