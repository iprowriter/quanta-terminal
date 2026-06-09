

## Activate Virtual Environment on New Terminal
source .venv/bin/activate

## Test An MCP Server with FastMCP Inspector
run `uv run fastmcp dev inspector mcp_servers/news_mcp.py`

-- Use shortcuts below:
make inspect-finance
make inspect-news
make inspect-sec
make inspect-research
make test        # runs test_mcp_servers.py
make sync        # uv sync

## Kill Port
lsof -ti :6274 | xargs kill -9 2>&1 && echo "killed"

 lsof -ti TCP:6274 | xargs kill -9 2>/dev/null; lsof -ti TCP:6277 | xargs kill -9 2>/dev/null; echo "done"
   Kill processes on ports 6274 and 6277 using TCP syntax

## Test the Graph (Orchestrator) in Development
`cd backend`
`uv run python agents/graph.py QUBT`

## FASTAPI Testing
cd backend
uv run uvicorn api.main:app --reload --port 8000


## Temmp
eyJhbGciOiJFUzI1NiIsImtpZCI6ImZmM2M2N2Y3LTQwNWYtNDdjNi1hM2E5LTc1NzIxOGI1YWI1NCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3hqYXhpY2pxcGViYnlncWl3cnRjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI5NWU2NmVhOC04NTI4LTQ0MmQtYTZlZi01NDZjM2E5Y2I0ZjYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgwOTE1NjcwLCJpYXQiOjE3ODA5MTIwNzAsImVtYWlsIjoibWFydGluQG1hcnRpbm9wdXRhLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJtYXJ0aW5AbWFydGlub3B1dGEuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiOTVlNjZlYTgtODUyOC00NDJkLWE2ZWYtNTQ2YzNhOWNiNGY2In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib3RwIiwidGltZXN0YW1wIjoxNzgwOTEyMDcwfV0sInNlc3Npb25faWQiOiIwNTkwYzEyYi1hNDViLTQzMjItYTM1OC00YTg2NjJhODQyNTciLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.YmpEdDHTs6JsJQPenDt0AhTwYz8Mg9OtqCPXvEnYXfVQav31h1YXLK01OHJzZGWZFDW86Z1SX0ds_1wPJVpdwg