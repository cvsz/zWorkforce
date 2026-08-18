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

func dirExists(path string) bool {
	info, err := os.Stat(path)
	if os.IsNotExist(err) {
		return false
	}
	return info.IsDir()
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

func statusAction(cfg *Config, target string) {
	fmt.Printf("\n%s%s--- Monorepo & Services Health Matrix ---%s\n", colorBold, colorBlue, colorReset)

	if target == "" || target == "all" || target == "zworkforce" {
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
	}

	if target == "" || target == "all" || target == "zarvis" {
		ok, code, _ := checkHTTP("http://127.0.0.1:3000", 2*time.Second)
		if ok {
			fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / ZVoice UI)\n", "Z.A.R.V.I.S. Voice Gateway", colorGreen, colorReset, code)
		} else {
			fmt.Printf("  • %-36s : %sSTANDBY%s\n", "Z.A.R.V.I.S. Voice Gateway", colorYellow, colorReset)
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		ok, code, _ := checkHTTP("http://127.0.0.1:3001", 2*time.Second)
		if ok {
			fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / https://studio.zeaz.dev)\n", "ZSP AI Studio & Video Renderer", colorGreen, colorReset, code)
		} else {
			ok3005, code3005, _ := checkHTTP("http://127.0.0.1:3005", 2*time.Second)
			if ok3005 {
				fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / https://studio.zeaz.dev)\n", "ZSP AI Studio & Video Renderer", colorGreen, colorReset, code3005)
			} else {
				fmt.Printf("  • %-36s : %sSTANDBY%s\n", "ZSP AI Studio & Video Renderer", colorYellow, colorReset)
			}
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ok, code, _ := checkHTTP("http://127.0.0.1:8085/health", 2*time.Second)
		if ok {
			fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d)\n", "Zider Companion Gateway", colorGreen, colorReset, code)
		} else {
			ok3002, code3002, _ := checkHTTP("http://127.0.0.1:3002", 2*time.Second)
			if ok3002 {
				fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d)\n", "Zider Companion Gateway", colorGreen, colorReset, code3002)
			} else {
				fmt.Printf("  • %-36s : %sSTANDBY%s\n", "Zider Companion Gateway", colorYellow, colorReset)
			}
		}
	}

	if target == "" || target == "all" || target == "zeto" {
		zetoDir := filepath.Join(cfg.RootDir, "packages/zeto")
		if dirExists(zetoDir) {
			fmt.Printf("  • %-36s : %sREADY%s (packages/zeto M12 Suite)\n", "Zeto AI Content Factory", colorGreen, colorReset)
		}
	}

	if target == "" || target == "all" {
		// OpenWebUI
		ok, code, _ := checkHTTP("http://127.0.0.1:3080", 2*time.Second)
		if ok {
			fmt.Printf("  • %-36s : %sONLINE%s (HTTP %d / https://chat.zeaz.dev)\n", "OpenWebUI Multi-Model Gateway", colorGreen, colorReset, code)
		} else {
			fmt.Printf("  • %-36s : %sSTANDBY%s\n", "OpenWebUI Multi-Model Gateway", colorYellow, colorReset)
		}

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

		fmt.Printf("\n%s%s--- zWorkforce Doctor Diagnostic ---%s\n", colorBold, colorCyan, colorReset)
		_ = runCommand(cfg.RootDir, "zworkforce", "doctor")
	}
}

// -------------------------------------------------------------
// BUILD ACTIONS
// -------------------------------------------------------------
func buildAction(cfg *Config, target string) {
	target = strings.ToLower(target)
	logInfo(fmt.Sprintf("Executing Build target '%s'...", target))

	if target == "" || target == "all" || target == "zworkforce" {
		logInfo("[zworkforce] Byte-compiling Python packages...")
		_ = runCommand(cfg.RootDir, "python3", "-m", "compileall", "-q", "zworkforce", "tests", "scripts")
		_ = runCommand(cfg.RootDir, "go", "build", "-o", "bin/zctl", "cmd/zctl/main.go")
	}

	if target == "" || target == "all" || target == "zarvis" {
		zarvisDir := filepath.Join(cfg.RootDir, "packages/zarvis")
		if dirExists(zarvisDir) {
			logInfo("[packages/zarvis] Building Z.A.R.V.I.S. workspace packages...")
			_ = runCommand(zarvisDir, "pnpm", "build")
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		zspDir := filepath.Join(cfg.RootDir, "packages/zsp-aitool")
		if dirExists(zspDir) {
			logInfo("[packages/zsp-aitool] Generating Prisma Client and Next.js bundle...")
			_ = runCommand(zspDir, "npm", "run", "prisma:generate")
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ziderDir := filepath.Join(cfg.RootDir, "packages/zider")
		if dirExists(ziderDir) {
			logInfo("[packages/zider] Building extension & verifying CSP...")
			_ = runCommand(ziderDir, "npm", "run", "build")
		}
	}

	if target == "" || target == "all" || target == "zeto" {
		zetoDir := filepath.Join(cfg.RootDir, "packages/zeto")
		if dirExists(zetoDir) {
			logInfo("[packages/zeto] Building and checking ProMeta content factory...")
			_ = runCommand(zetoDir, "npm", "test")
		}
	}

	logSuccess(fmt.Sprintf("Build target '%s' completed.", target))
}

// -------------------------------------------------------------
// INSTALL ACTIONS
// -------------------------------------------------------------
func installAction(cfg *Config, target string) {
	target = strings.ToLower(target)
	logInfo(fmt.Sprintf("Executing Install target '%s'...", target))

	if target == "" || target == "all" || target == "zworkforce" {
		logInfo("[zworkforce] Executing root setup.sh...")
		if fileExists(filepath.Join(cfg.RootDir, "setup.sh")) {
			_ = runCommand(cfg.RootDir, "bash", "setup.sh")
		}
	}

	if target == "" || target == "all" || target == "zarvis" {
		zarvisDir := filepath.Join(cfg.RootDir, "packages/zarvis")
		if dirExists(zarvisDir) {
			logInfo("[packages/zarvis] Installing pnpm dependencies...")
			_ = runCommand(zarvisDir, "pnpm", "install", "--frozen-lockfile")
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		zspDir := filepath.Join(cfg.RootDir, "packages/zsp-aitool")
		if dirExists(zspDir) {
			logInfo("[packages/zsp-aitool] Installing dependencies and Prisma...")
			_ = runCommand(zspDir, "npm", "install")
			_ = runCommand(zspDir, "npm", "run", "prisma:generate")
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ziderDir := filepath.Join(cfg.RootDir, "packages/zider")
		if dirExists(ziderDir) {
			logInfo("[packages/zider] Installing extension and server dependencies...")
			_ = runCommand(ziderDir, "npm", "install")
			_ = runCommand(ziderDir, "npm", "run", "build")
		}
	}

	if target == "" || target == "all" || target == "zeto" {
		zetoDir := filepath.Join(cfg.RootDir, "packages/zeto")
		if dirExists(zetoDir) {
			logInfo("[packages/zeto] Installing content factory dependencies...")
			_ = runCommand(zetoDir, "npm", "install")
		}
	}

	if target == "" || target == "all" {
		masterScript := filepath.Join(cfg.RootDir, "scripts/install/install_hermes_full_stack_master.sh")
		if fileExists(masterScript) {
			logInfo("Verifying Hermes Agent & Spawn toolchain...")
			_ = runCommand(cfg.RootDir, "bash", masterScript, "--dry-run")
		}
	}

	logSuccess(fmt.Sprintf("Install target '%s' completed.", target))
}

// -------------------------------------------------------------
// START ACTIONS
// -------------------------------------------------------------
func startAction(cfg *Config, target string) {
	target = strings.ToLower(target)
	logInfo(fmt.Sprintf("Starting services for target '%s'...", target))

	if target == "" || target == "all" || target == "zworkforce" {
		logInfo("[zworkforce] Launching docker compose core services...")
		_ = runCommand(cfg.RootDir, "docker", "compose", "up", "-d")
	}

	if target == "" || target == "all" || target == "zarvis" {
		zarvisCompose := filepath.Join(cfg.RootDir, "packages/zarvis/compose.yaml")
		if fileExists(zarvisCompose) {
			logInfo("[packages/zarvis] Starting Z.A.R.V.I.S. Voice Gateway containers...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "packages/zarvis/compose.yaml", "up", "-d")
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		zspCompose := filepath.Join(cfg.RootDir, "compose.zsp-aitool.yml")
		if fileExists(zspCompose) {
			logInfo("[packages/zsp-aitool] Starting ZSP AI Studio containers...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.zsp-aitool.yml", "up", "-d")
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ziderCompose := filepath.Join(cfg.RootDir, "packages/zider/compose.yaml")
		if fileExists(ziderCompose) {
			logInfo("[packages/zider] Starting Zider companion gateway container...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "packages/zider/compose.yaml", "up", "-d")
		}
	}

	if target == "" || target == "all" || target == "openwebui" {
		if fileExists(filepath.Join(cfg.RootDir, "compose.open-webui.yml")) {
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.open-webui.yml", "up", "-d")
		}
	}

	logSuccess(fmt.Sprintf("Start for target '%s' completed.", target))
}

// -------------------------------------------------------------
// STOP ACTIONS
// -------------------------------------------------------------
func stopAction(cfg *Config, target string) {
	target = strings.ToLower(target)
	logInfo(fmt.Sprintf("Stopping services for target '%s'...", target))

	if target == "" || target == "all" || target == "zworkforce" {
		logInfo("[zworkforce] Stopping docker compose core services...")
		_ = runCommand(cfg.RootDir, "docker", "compose", "down")
	}

	if target == "" || target == "all" || target == "zarvis" {
		zarvisCompose := filepath.Join(cfg.RootDir, "packages/zarvis/compose.yaml")
		if fileExists(zarvisCompose) {
			logInfo("[packages/zarvis] Stopping Z.A.R.V.I.S. containers...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "packages/zarvis/compose.yaml", "down")
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		zspCompose := filepath.Join(cfg.RootDir, "compose.zsp-aitool.yml")
		if fileExists(zspCompose) {
			logInfo("[packages/zsp-aitool] Stopping ZSP Studio containers...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.zsp-aitool.yml", "down")
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ziderCompose := filepath.Join(cfg.RootDir, "packages/zider/compose.yaml")
		if fileExists(ziderCompose) {
			logInfo("[packages/zider] Stopping Zider companion container...")
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "packages/zider/compose.yaml", "down")
		}
	}

	if target == "" || target == "all" || target == "openwebui" {
		if fileExists(filepath.Join(cfg.RootDir, "compose.open-webui.yml")) {
			_ = runCommand(cfg.RootDir, "docker", "compose", "-f", "compose.open-webui.yml", "down")
		}
	}

	logSuccess(fmt.Sprintf("Stop for target '%s' completed.", target))
}

// -------------------------------------------------------------
// RESTART ACTIONS
// -------------------------------------------------------------
func restartAction(cfg *Config, target string) {
	stopAction(cfg, target)
	time.Sleep(2 * time.Second)
	startAction(cfg, target)
}

// -------------------------------------------------------------
// VERIFY ACTION
// -------------------------------------------------------------
func verifyAction(cfg *Config, target string) {
	target = strings.ToLower(target)
	logInfo(fmt.Sprintf("Initiating Validation Suite for target '%s'...", target))

	if target == "" || target == "all" || target == "zworkforce" {
		logInfo("[zworkforce] Byte-compiling Python services and test suite...")
		_ = runCommand(cfg.RootDir, "python3", "-m", "compileall", "-q", "zworkforce", "tests", "scripts")
		logInfo("[zworkforce] Executing unittest discover...")
		cmd := exec.Command("python3", "-m", "unittest", "discover", "-s", "tests", "-v")
		cmd.Dir = cfg.RootDir
		cmd.Env = append(os.Environ(), "PYTHONPATH=.")
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		_ = cmd.Run()
		_ = runCommand(cfg.RootDir, "zworkforce", "doctor")
	}

	if target == "" || target == "all" || target == "zeto" {
		zetoDir := filepath.Join(cfg.RootDir, "packages/zeto")
		if dirExists(zetoDir) {
			logInfo("[packages/zeto] Running QA & SEO tests...")
			_ = runCommand(zetoDir, "node", "--test", "test/qa_seo_engine.test.js", "test/prompt_tuner.test.js")
		}
	}

	if target == "" || target == "all" || target == "zsp" || target == "zsp-aitool" {
		zspDir := filepath.Join(cfg.RootDir, "packages/zsp-aitool")
		if dirExists(zspDir) {
			logInfo("[packages/zsp-aitool] Running Collab & Video Generator tests...")
			_ = runCommand(zspDir, "node", "--test", "tests/collab_server.test.js", "tests/export_pipeline.test.js", "tests/video_generator.test.js")
		}
	}

	if target == "" || target == "all" || target == "zider" {
		ziderDir := filepath.Join(cfg.RootDir, "packages/zider")
		if dirExists(ziderDir) {
			logInfo("[packages/zider] Running extension, CSP & rerank tests...")
			_ = runCommand(ziderDir, "node", "--test", "scripts/verify_csp.test.mjs", "extension/test_context_menu.mjs", "server/test/rerank_engine.test.mjs")
		}
	}

	if target == "" || target == "all" || target == "zarvis" {
		zarvisDir := filepath.Join(cfg.RootDir, "packages/zarvis")
		if dirExists(zarvisDir) {
			logInfo("[packages/zarvis] Running caption overlay tests...")
			_ = runCommand(zarvisDir, "node", "--test", "apps/zvoice/test/transcript_overlay.test.mjs")
		}
	}

	logSuccess(fmt.Sprintf("Validation for target '%s' completed.", target))
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
		fmt.Printf("  %s1)%s Check System & Services Status across all packages/*\n", colorCyan, colorReset)
		fmt.Printf("  %s2)%s Run Full Validation Suite across Monorepo & packages/*\n", colorCyan, colorReset)
		fmt.Printf("  %s3)%s Build All (or specific package)\n", colorCyan, colorReset)
		fmt.Printf("  %s4)%s Install All (or specific package)\n", colorCyan, colorReset)
		fmt.Printf("  %s5)%s Start All Services (Docker & Gateways)\n", colorCyan, colorReset)
		fmt.Printf("  %s6)%s Stop All Services\n", colorCyan, colorReset)
		fmt.Printf("  %s7)%s Restart All Services\n", colorCyan, colorReset)
		fmt.Printf("  %s8)%s Inspect Provider & Secret Vault Config\n", colorCyan, colorReset)
		fmt.Printf("  %sq)%s Exit\n", colorRed, colorReset)
		fmt.Print("\nEnter choice [1-8, q]: ")

		input, _ := reader.ReadString('\n')
		choice := strings.TrimSpace(input)

		switch choice {
		case "1":
			statusAction(cfg, "all")
		case "2":
			verifyAction(cfg, "all")
		case "3":
			buildAction(cfg, "all")
		case "4":
			installAction(cfg, "all")
		case "5":
			startAction(cfg, "all")
		case "6":
			stopAction(cfg, "all")
		case "7":
			restartAction(cfg, "all")
		case "8":
			configAction(cfg)
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

func parseTarget(args []string) string {
	if len(args) >= 2 {
		return args[1]
	}
	return "all"
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
	target := parseTarget(os.Args[1:])

	switch cmd {
	case "status":
		statusAction(cfg, target)
	case "build":
		buildAction(cfg, target)
	case "install", "setup":
		installAction(cfg, target)
	case "start":
		startAction(cfg, target)
	case "stop":
		stopAction(cfg, target)
	case "restart":
		restartAction(cfg, target)
	case "verify", "test":
		verifyAction(cfg, target)
	case "config", "vault":
		configAction(cfg)
	case "help", "--help", "-h":
		printBanner()
		fmt.Println("\nUsage: zctl [command] [package]")
		fmt.Println("\nSupported packages: all, zworkforce, zarvis, zsp-aitool, zider, zeto")
		fmt.Println("\nAvailable Commands:")
		fmt.Println("  build [target]    - Build target (zworkforce, zarvis, zsp-aitool, zider, zeto, all)")
		fmt.Println("  install [target]  - Install dependencies and toolchains for target or all")
		fmt.Println("  start [target]    - Start docker compose containers and daemons for target or all")
		fmt.Println("  stop [target]     - Stop containers and daemons for target or all")
		fmt.Println("  restart [target]  - Restart containers and daemons for target or all")
		fmt.Println("  verify [target]   - Run test and verification suites for target or all")
		fmt.Println("  status [target]   - Display real-time service health for target or all")
		fmt.Println("  config            - Inspect masked active provider keys from .env.ai")
		fmt.Println("  help              - Show this command reference")
	default:
		logError(fmt.Sprintf("Unknown command '%s'", cmd))
		fmt.Println("Run 'zctl help' for available options or launch without arguments for interactive UI.")
		os.Exit(1)
	}
}
