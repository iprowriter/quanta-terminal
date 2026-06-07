.PHONY: sync dev \
        inspect-finance inspect-news inspect-sec inspect-research \
        agent-finance \
        test lint format typecheck check \
        migrate migration db-reset

# ── Dependencies ───────────────────────────────────────────────────────────────

sync:
	uv sync

# ── API server ─────────────────────────────────────────────────────────────────

dev:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── MCP Inspector ──────────────────────────────────────────────────────────────

INSPECTOR = uv run fastmcp dev inspector

inspect-finance:
	$(INSPECTOR) mcp_servers/finance_mcp.py

inspect-news:
	$(INSPECTOR) mcp_servers/news_mcp.py

inspect-sec:
	$(INSPECTOR) mcp_servers/sec_mcp.py

inspect-research:
	$(INSPECTOR) mcp_servers/research_mcp.py

# ── Agents ─────────────────────────────────────────────────────────────────────

agent-finance:
	uv run python agents/finance_agent.py

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	uv run python test_mcp_servers.py

# ── Code quality ───────────────────────────────────────────────────────────────

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright .

check: lint typecheck test

# ── Database ───────────────────────────────────────────────────────────────────

migrate:
	uv run alembic upgrade head

# Usage: make migration name="add users table"
migration:
	uv run alembic revision --autogenerate -m "$(name)"

db-reset:
	uv run alembic downgrade base && uv run alembic upgrade head
