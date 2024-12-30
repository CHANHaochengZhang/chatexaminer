# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
PORT = 8000
HOST = 0.0.0.0
SHELL := /bin/bash  # Ensure using bash

# Colors for terminal output
BLUE = \033[0;34m
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[1;33m
NC = \033[0m # No Color

# System dependencies for Ubuntu/Debian
system-deps:
	@echo "$(BLUE)Installing system dependencies...$(NC)"
	sudo apt update
	sudo apt install -y python3-full python3-pip python3-venv build-essential curl pkg-config libssl-dev

	@echo "$(BLUE)Installing Rust...$(NC)"
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

	@echo "$(BLUE)Adding Rust to PATH...$(NC)"
	echo 'source $$HOME/.cargo/env' >> ~/.bashrc
	. $$HOME/.cargo/env

# Create and setup virtual environment
setup-venv:
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	python3 -m venv $(VENV)
	@echo "$(BLUE)Activating virtual environment...$(NC)"
	. $(VENV)/bin/activate && \
	$(PIP) install --upgrade pip setuptools wheel

# Install Python dependencies with Rust environment
install-deps: setup-venv
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	. $(VENV)/bin/activate && \
	source $$HOME/.cargo/env && \
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

# Download NLTK data
setup-nltk: install-deps
	@echo "$(BLUE)Downloading NLTK data...$(NC)"
	. $(VENV)/bin/activate && \
	$(PYTHON) -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

# Complete setup
setup: system-deps install-deps setup-nltk
	@echo "$(GREEN)Setup completed successfully!$(NC)"
	@echo "$(YELLOW)To activate the virtual environment, run:$(NC)"
	@echo "source $(VENV)/bin/activate"

# Clean up
clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Run backend server
run-backend:
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	. $(VENV)/bin/activate && \
	uvicorn server.app.main:app --reload --host $(HOST) --port $(PORT)

# Update dependencies
update-deps:
	@echo "$(BLUE)Updating dependencies...$(NC)"
	. $(VENV)/bin/activate && \
	source $$HOME/.cargo/env && \
	$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)Dependencies updated!$(NC)"

# Run tests
test:
	@echo "$(BLUE)Running tests...$(NC)"
	. $(VENV)/bin/activate && \
	python -m pytest

# Run linter
lint:
	@echo "$(BLUE)Running linter...$(NC)"
	. $(VENV)/bin/activate && \
	python -m flake8

.PHONY: system-deps setup-venv install-deps setup-nltk setup clean run-backend update-deps test lint

# Help command
help:
	@echo "$(BLUE)Available commands:$(NC)"
	@echo "$(GREEN)make system-deps$(NC)  - Install system dependencies"
	@echo "$(GREEN)make setup$(NC)        - Complete setup (system deps + venv + Python deps + NLTK)"
	@echo "$(GREEN)make clean$(NC)        - Remove virtual environment and cached files"
	@echo "$(GREEN)make run-backend$(NC)  - Start the FastAPI server"
	@echo "$(GREEN)make update-deps$(NC)  - Update dependencies to latest versions"
	@echo "$(GREEN)make test$(NC)         - Run tests"
	@echo "$(GREEN)make lint$(NC)         - Run linter"
