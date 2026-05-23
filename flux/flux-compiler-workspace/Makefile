# FLUX Compiler Workspace — Makefile
# Build, test, bench, lint, and install targets

# ── Config ──────────────────────────────────────────────
CARGO    := cargo
RELEASE  := --release
WORKSPACE:= --workspace
ALL_FEAT := --all-features

# ── Colors ──────────────────────────────────────────────
RESET    := \033[0m
BOLD     := \033[1m
GREEN    := \033[32m
YELLOW   := \033[33m
CYAN     := \033[36m
RED      := \033[31m

# ── Phony targets ───────────────────────────────────────
.PHONY: all build build-dev test bench lint fmt clippy clean install check doc help

# ── Default ─────────────────────────────────────────────
all: build

# ── Build ───────────────────────────────────────────────
build: ## Build all crates in release mode
	@echo "$(BOLD)$(CYAN)⚒️  Building FLUX (release)...$(RESET)"
	$(CARGO) build $(RELEASE) $(WORKSPACE)
	@echo "$(BOLD)$(GREEN)✓ Build complete$(RESET)"

build-dev: ## Build all crates in debug mode
	@echo "$(BOLD)$(CYAN)⚒️  Building FLUX (debug)...$(RESET)"
	$(CARGO) build $(WORKSPACE)
	@echo "$(BOLD)$(GREEN)✓ Debug build complete$(RESET)"

check: ## Quick check (no codegen)
	@echo "$(BOLD)$(CYAN)⚡ Checking FLUX workspace...$(RESET)"
	$(CARGO) check $(WORKSPACE) $(ALL_FEAT)
	@echo "$(BOLD)$(GREEN)✓ Check passed$(RESET)"

# ── Test ────────────────────────────────────────────────
test: ## Run all tests
	@echo "$(BOLD)$(CYAN)🧪 Running tests...$(RESET)"
	$(CARGO) test $(WORKSPACE) $(ALL_FEAT)
	@echo "$(BOLD)$(GREEN)✓ All tests passed$(RESET)"

test-release: ## Run tests in release mode
	@echo "$(BOLD)$(CYAN)🧪 Running tests (release)...$(RESET)"
	$(CARGO) test $(WORKSPACE) $(RELEASE)
	@echo "$(BOLD)$(GREEN)✓ All release tests passed$(RESET)"

# ── Bench ───────────────────────────────────────────────
bench: ## Run benchmarks
	@echo "$(BOLD)$(YELLOW)📊 Running benchmarks...$(RESET)"
	$(CARGO) bench $(WORKSPACE)
	@echo "$(BOLD)$(GREEN)✓ Benchmarks complete$(RESET)"

# ── Lint ────────────────────────────────────────────────
lint: fmt clippy ## Run all linters (fmt + clippy)

fmt: ## Check formatting
	@echo "$(BOLD)$(CYAN)📐 Checking formatting...$(RESET)"
	$(CARGO) fmt --all -- --check
	@echo "$(BOLD)$(GREEN)✓ Formatting OK$(RESET)"

fmt-fix: ## Fix formatting
	@echo "$(BOLD)$(CYAN)📐 Fixing formatting...$(RESET)"
	$(CARGO) fmt --all

clippy: ## Run clippy (warnings as errors)
	@echo "$(BOLD)$(CYAN)🔍 Running clippy...$(RESET)"
	$(CARGO) clippy $(WORKSPACE) $(ALL_FEAT) -- -D warnings
	@echo "$(BOLD)$(GREEN)✓ Clippy clean$(RESET)"

clippy-fix: ## Run clippy with auto-fix
	@echo "$(BOLD)$(CYAN)🔍 Running clippy (fix)...$(RESET)"
	$(CARGO) clippy --fix $(WORKSPACE) $(ALL_FEAT) --allow-dirty

# ── Docs ────────────────────────────────────────────────
doc: ## Generate documentation
	@echo "$(BOLD)$(CYAN)📖 Generating docs...$(RESET)"
	$(CARGO) doc $(WORKSPACE) --no-deps
	@echo "$(BOLD)$(GREEN)✓ Docs at target/doc$(RESET)"

# ── Install ─────────────────────────────────────────────
install: build ## Install fluxc CLI
	@echo "$(BOLD)$(YELLOW)📦 Installing fluxc...$(RESET)"
	$(CARGO) install --path crates/fluxc-cli
	@echo "$(BOLD)$(GREEN)✓ fluxc installed$(RESET)"

# ── Clean ───────────────────────────────────────────────
clean: ## Remove build artifacts
	@echo "$(BOLD)$(RED)🗑️  Cleaning build artifacts...$(RESET)"
	$(CARGO) clean
	@echo "$(BOLD)$(GREEN)✓ Clean$(RESET)"

# ── Help ────────────────────────────────────────────────
help: ## Show this help
	@echo "$(BOLD)$(CYAN)FLUX Compiler Workspace$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-16s$(RESET) %s\n", $$1, $$2}'
