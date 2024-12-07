.DEFAULT_GOAL := help

.PHONY: help
help:  ## Shows this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target> <arg=value>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m  %s\033[0m\n\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 🚀 Tools 
lint:  ## lint code
	@uv run ruff format . --check
	@uv run ruff check .

typecheck: ## typecheck code
	@uv run mypy .

check-all: lint typecheck  ## run all checkers

format:  ## use ruff to fix all linting problems
	@uv run ruff format .
	@uv run ruff check . --fix
