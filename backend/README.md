

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