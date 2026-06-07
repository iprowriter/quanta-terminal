"""
News Agent
LangGraph agent that analyses news sentiment, coverage spikes, and sector developments.

Tools: search_news · detect_news_spike · get_sector_news
Memory: MemorySaver (per-thread conversation history)
"""

import operator
import uuid
import asyncio
import sys
from pathlib import Path
from typing import Annotated, Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing_extensions import TypedDict

from prompts.system_prompts import news_system_prompt
from core.config import settings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).parent.parent
MCP_DIR = BACKEND_DIR / "mcp_servers"

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class NewsState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    # Cached tool outputs — populated on first tool call, reused downstream
    news_articles: dict[str, Any]
    news_spike: dict[str, Any]
    sector_news: dict[str, Any]


# ---------------------------------------------------------------------------
# Module-level singletons (kept alive so MCP subprocesses are not GC'd)
# ---------------------------------------------------------------------------

_mcp_client: MultiServerMCPClient | None = None
_graph = None
_checkpointer = MemorySaver()

_NEWS_TOOL_NAMES = {
    "search_news",
    "detect_news_spike",
    "get_sector_news",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mcp_env() -> dict:
    """Ensure backend/ is on PYTHONPATH for the MCP subprocess."""
    import os
    env = os.environ.copy()
    backend = str(BACKEND_DIR)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend}:{existing}" if existing else backend
    return env


def _build_model():
    """Return a Gemini or Ollama chat model based on settings."""
    if settings.llm_provider == "ollama":
        return init_chat_model(
            settings.ollama_model,
            model_provider="ollama",
            temperature=0,
        )
    return init_chat_model(
        settings.gemini_model,
        model_provider=settings.model_provider,
        temperature=0,
        api_key=settings.google_api_key,
    )


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

async def llm_call(state: NewsState, model_with_tools) -> dict:
    """Send messages to the LLM and return the response."""
    system = SystemMessage(content=news_system_prompt)
    response = await model_with_tools.ainvoke([system] + state["messages"])
    return {"messages": [response]}


async def tool_node(state: NewsState, tools_by_name: dict[str, BaseTool]) -> dict:
    """Execute all tool calls from the last LLM message concurrently."""
    last_message = state["messages"][-1]
    assert isinstance(last_message, AIMessage)
    tool_calls = last_message.tool_calls

    async def _run(tool_call):
        tool = tools_by_name[tool_call["name"]]
        result = await tool.ainvoke(tool_call["args"])
        return ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"],
            name=tool_call["name"],
        )

    tool_messages = await asyncio.gather(*[_run(tc) for tc in tool_calls])

    cache_updates: dict[str, Any] = {}
    for tc in tool_calls:
        if tc["name"] == "search_news":
            cache_updates["news_articles"] = tc["args"]
        elif tc["name"] == "detect_news_spike":
            cache_updates["news_spike"] = tc["args"]
        elif tc["name"] == "get_sector_news":
            cache_updates["sector_news"] = tc["args"]

    return {"messages": list(tool_messages), **cache_updates}


def should_continue(state: NewsState) -> str:
    """Route: call tools, end, or force-end if the agent loops excessively."""
    last = state["messages"][-1]

    llm_calls = sum(
        1 for m in state["messages"]
        if isinstance(m, AIMessage) and m.tool_calls
    )
    if llm_calls >= 6:
        return END

    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def initialize() -> None:
    """
    Wire up MCP tools and compile the graph.
    Call once at FastAPI app lifespan startup — not lazily per request.
    """
    global _mcp_client, _graph

    if _graph is not None:
        return

    _mcp_client = MultiServerMCPClient(
        {
            "news": {
                "command": sys.executable,
                "args": [str(MCP_DIR / "news_mcp.py")],
                "transport": "stdio",
                "env": _mcp_env(),
            }
        }
    )

    all_tools = await _mcp_client.get_tools()
    tools = [t for t in all_tools if t.name in _NEWS_TOOL_NAMES]
    tools_by_name = {t.name: t for t in tools}

    model = _build_model()
    model_with_tools = model.bind_tools(tools)

    async def _llm_call(state: NewsState):
        return await llm_call(state, model_with_tools)

    async def _tool_node(state: NewsState):
        return await tool_node(state, tools_by_name)

    builder = StateGraph(NewsState)
    builder.add_node("llm_call", _llm_call)
    builder.add_node("tools", _tool_node)

    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "llm_call")

    _graph = builder.compile(checkpointer=_checkpointer)


async def generate_response(
    query: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Run the news agent and return a structured result.

    Returns:
        {
            "text":          str  — the agent's final response,
            "thread_id":     str  — pass back to continue this conversation,
            "news_articles": dict — cached search_news output,
            "news_spike":    dict — cached detect_news_spike output,
            "sector_news":   dict — cached get_sector_news output,
        }
    """
    if _graph is None:
        raise RuntimeError("News agent not initialised — call initialize() first.")

    thread_id = thread_id or str(uuid.uuid4())

    initial_state: NewsState = {
        "messages": [HumanMessage(content=query)],
        "news_articles": {},
        "news_spike": {},
        "sector_news": {},
    }

    result = await _graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}},
    )

    return {
        "text": result["messages"][-1].content,
        "thread_id": thread_id,
        "news_articles": result.get("news_articles", {}),
        "news_spike": result.get("news_spike", {}),
        "sector_news": result.get("sector_news", {}),
    }


# ---------------------------------------------------------------------------
# Dev REPL
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    async def _main() -> None:
        await initialize()
        print("News Agent ready. Type 'quit' to exit, 'new' to start a fresh thread.\n")
        thread_id: str | None = None

        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                break
            if query.lower() == "new":
                thread_id = None
                print("(new conversation started)\n")
                continue

            result = await generate_response(query, thread_id=thread_id)
            thread_id = result["thread_id"]
            print(f"\nAgent: {result['text']}\n")

    asyncio.run(_main())
