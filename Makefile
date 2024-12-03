 # Variables
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
SERVER_DIR = server
PORT = 8000
HOST = 0.0.0.0

# Colors for terminal output
BLUE = \033[0;34m
GREEN = \033[0;32m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help setup clean run install update-deps test lint

help:
	@echo "$(BLUE)Available commands:$(NC)"
	@echo "$(GREEN)make setup$(NC)      - Create virtual environment and install dependencies"
	@echo "$(GREEN)make clean$(NC)      - Remove virtual environment and cached files"
	@echo "$(GREEN)make run$(NC)        - Start the FastAPI server"
	@echo "$(GREEN)make install$(NC)    - Install dependencies"
	@echo "$(GREEN)make update-deps$(NC) - Update dependencies to latest versions"
	@echo "$(GREEN)make test$(NC)       - Run tests"
	@echo "$(GREEN)make lint$(NC)       - Run linter"

setup:
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	python3 -m venv $(VENV)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r $(SERVER_DIR)/requirements.txt
	@echo "$(GREEN)Setup complete!$(NC)"

clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleanup complete!$(NC)"

run-backend:
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	cd $(SERVER_DIR) && uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

install:
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r $(SERVER_DIR)/requirements.txt
	@echo "$(GREEN)Installation complete!$(NC)"

update-deps:
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade -r $(SERVER_DIR)/requirements.txt
	@echo "$(GREEN)Dependencies updated!$(NC)"

test:
	@echo "$(BLUE)Running tests...$(NC)"
	cd $(SERVER_DIR) && ../$(PYTHON) -m pytest

lint:
	@echo "$(BLUE)Running linter...$(NC)"
	cd $(SERVER_DIR) && ../$(PYTHON) -m flake8
