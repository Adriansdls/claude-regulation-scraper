# Claude Regulation Scraper - Makefile
.PHONY: help install install-dev test clean setup deps run-discovery run-monitoring

# Default target
help:
	@echo "🤖 Claude Regulation Scraper - Available Commands:"
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install      - Install the CLI tool"
	@echo "  make install-dev  - Install in development mode" 
	@echo "  make deps         - Install dependencies only"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup        - Setup API keys and configuration"
	@echo "  make run-discovery - Run discovery for US jurisdictions"
	@echo "  make run-monitoring - Run monitoring for discovered sources"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-simple  - Run simple agent test"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "💡 CLI Usage:"
	@echo "  claude-reg --help           - Show all commands"
	@echo "  claude-reg quick-start      - Show quick start guide"
	@echo "  claude-reg discover --help  - Discovery commands help"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

deps:
	pip install -r requirements.txt

# Setup and configuration
setup:
	@echo "🚀 Setting up Claude Regulation Scraper..."
	@echo ""
	@echo "Please enter your API keys:"
	@read -p "OpenAI API Key: " openai_key; \
	claude-reg config set-api-key openai $$openai_key
	@read -p "Firecrawl API Key (optional): " firecrawl_key; \
	if [ ! -z "$$firecrawl_key" ]; then claude-reg config set-api-key firecrawl $$firecrawl_key; fi
	@echo ""
	@echo "✅ Setup complete! Run 'make run-discovery' to get started."

# Quick run targets  
run-discovery:
	claude-reg discover jurisdictions --jurisdictions US,UK --agencies FDA,CPSC --output table

run-monitoring:
	claude-reg monitor run --jurisdictions US --output table

# Testing targets
test:
	python test_publication_discovery_system.py

test-simple:
	python test_simple_discovery.py

test-cli:
	@echo "🧪 Testing CLI commands..."
	claude-reg --help
	claude-reg config show
	claude-reg sources list
	@echo "✅ CLI tests complete"

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Development helpers
lint:
	black .
	isort .

format: lint

check:
	python -m py_compile claude_regulation_scraper.py
	python -m py_compile test_publication_discovery_system.py

# Docker targets (if needed later)
docker-build:
	docker build -t claude-regulation-scraper .

docker-run:
	docker run -it --rm claude-regulation-scraper

# Documentation
docs:
	@echo "📚 Generating documentation..."
	claude-reg --help > docs/cli-help.txt
	claude-reg discover --help >> docs/cli-help.txt
	claude-reg sources --help >> docs/cli-help.txt  
	claude-reg monitor --help >> docs/cli-help.txt
	claude-reg config --help >> docs/cli-help.txt
	@echo "✅ Documentation generated in docs/"