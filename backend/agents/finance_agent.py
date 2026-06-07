"""
Finance Agent
LangGraph ReAct agent that uses finance MCP tools to analyze stocks.
"""

import os
import sys
import asyncio
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

BACKEND_DIR = Path(__file__).parent.parent
MCP_DIR = BACKEND_DIR / "mcp_servers"

SYSTEM_PROMPT = """You are a financial analyst for Quanta Terminal, a platform focused on \
emerging compute stocks — quantum computing, AI semiconductors, and related sectors.

You have access to the following real-time financial tools:
- get_stock_info: current price, market cap, volume, company overview
- get_financials: revenue, cash, debt, margins, valuation ratios
- get_earnings: EPS history, upcoming earnings date, quarterly growth
- get_analyst_recommendations: price targets, analyst ratings
- get_price_history: historical OHLCV data for trend analysis

When analysing a stock:
1. Always start with get_stock_info for context
2. Use get_financials to assess the financial health and burn rate
3. Use get_earnings to evaluate EPS trends and upcoming catalysts
4. Pull get_analyst_recommendations for Wall Street sentiment
5. Use get_price_history only when the user asks about price trends or chart patterns

Be concise and data-driven. Always cite specific numbers. Flag key risks and catalysts. \
Do not speculate beyond what the data shows."""


def _mcp_env() -> dict:
    """Ensure the backend/ directory is on PYTHONPATH for the MCP subprocess."""
    env = os.environ.copy()
    backend = str(BACKEND_DIR)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend}:{existing}" if existing else backend
    return env


_checkpointer = InMemorySaver()
_agent = None


async def get_finance_agent():
    """Return the finance agent, building it once and caching it."""
    global _agent
    if _agent is not None:
        return _agent

    client = MultiServerMCPClient(
        {
            "finance": {
                "command": sys.executable, # python
                "args": [str(MCP_DIR / "finance_mcp.py")],
                "transport": "stdio",
                "env": _mcp_env(),
            }
        }
    )
    tools = await client.get_tools()

    model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    _agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=_checkpointer,
    )
    return _agent


async def run(query: str, thread_id: str = "default") -> str:
    """Run the finance agent and return the final response text."""
    agent = await get_finance_agent()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    async def _main() -> None:
        print("Finance Agent ready. Type 'quit' to exit.\n")
        thread_id = "dev-session"
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                break
            response = await run(query, thread_id=thread_id)
            print(f"\nAgent: {response}\n")

    asyncio.run(_main())
