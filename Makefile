.ONESHELL:
# Use bash so `pipefail` works (dash `/bin/sh` doesn't support it)
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

VENV_DIR ?= .venv
PY ?= python3
PIP ?= $(VENV_DIR)/bin/pip
COMPOSE ?= docker compose

MOCK_PORT ?= 5000
PIPELINE_PORT ?= 8000

DATABASE_URL_LOCAL ?= postgresql://postgres:password@localhost:5432/customer_db
MOCK_SERVER_URL_LOCAL ?= http://localhost:$(MOCK_PORT)

.PHONY: help
help:
	@printf "%s\n" \
	"Targets:" \
	"  venv                 Create local virtualenv in $(VENV_DIR)" \
	"  install              Install mock-server and pipeline-service deps into venv" \
	"  install-test         Install test dependencies" \
	"  db-up                Start ONLY Postgres via docker compose" \
	"  db-down              Stop Postgres (and other compose services if running)" \
	"  run-native-mock      Run Flask mock server locally (uses venv)" \
	"  run-native-pipeline  Run FastAPI pipeline locally (uses venv, talks to db container)" \
	"  run-native           Start db container + run both services locally (two terminals recommended)" \
	"  compose-up           Start ALL services via docker compose" \
	"  compose-down         Stop ALL services via docker compose" \
	"  compose-build        Build compose images" \
	"  compose-logs         Tail compose logs" \
	"  compose-test-up      Start services with TEST database (customer_db_test)" \
	"  compose-test-down    Stop test services and clean up test database" \
	"  compose-test-logs    Tail test services logs" \
	"  test                 Run integration tests (auto starts/stops test services)" \
	"  test-verbose         Run integration tests with verbose output (auto starts/stops)"

.PHONY: venv
venv:
	$(PY) -m venv "$(VENV_DIR)"
	"$(VENV_DIR)/bin/python" -m pip install --upgrade pip

.PHONY: install
install: venv
	$(PIP) install -r mock-server/requirements.txt
	$(PIP) install -r pipeline-service/requirements.txt

.PHONY: db-up
db-up:
	$(COMPOSE) up -d postgres

.PHONY: db-down
db-down:
	$(COMPOSE) down

.PHONY: run-native-mock
run-native-mock: install
	cd mock-server
	"../$(VENV_DIR)/bin/gunicorn" --bind "0.0.0.0:$(MOCK_PORT)" "app:app"

.PHONY: run-native-pipeline
run-native-pipeline: install
	cd pipeline-service
	export DATABASE_URL="$(DATABASE_URL_LOCAL)"
	export MOCK_SERVER_URL="$(MOCK_SERVER_URL_LOCAL)"
	"../$(VENV_DIR)/bin/uvicorn" "main:app" --host "0.0.0.0" --port "$(PIPELINE_PORT)"

.PHONY: run-native
run-native: db-up
	@printf "%s\n" \
	"Postgres is starting in Docker." \
	"Run these in two terminals:" \
	"  make run-native-mock" \
	"  make run-native-pipeline"

.PHONY: compose-up
compose-up:
	$(COMPOSE) up -d

.PHONY: compose-down
compose-down:
	$(COMPOSE) down

.PHONY: compose-build
compose-build:
	$(COMPOSE) build

.PHONY: compose-logs
compose-logs:
	$(COMPOSE) logs -f

.PHONY: install-test
install-test: venv
	$(PIP) install -r requirements.txt

.PHONY: compose-test-up
compose-test-up:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.test.yml up -d

.PHONY: compose-test-down
compose-test-down:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.test.yml down -v

.PHONY: compose-test-logs
compose-test-logs:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.test.yml logs -f

.PHONY: test
test: install-test compose-test-up
	@sleep 3
	"$(VENV_DIR)/bin/pytest" tests/ -v --tb=short || true
	$(MAKE) compose-test-down

.PHONY: test-verbose
test-verbose: install-test compose-test-up
	@sleep 3
	"$(VENV_DIR)/bin/pytest" tests/ -vv --tb=long -s || true
	$(MAKE) compose-test-down
