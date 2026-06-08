"""
Pipeline Graph
LangGraph pipeline: Orchestrator → 5 specialist agents (parallel) → Memo Writer.

Each specialist agent has its own internal ReAct graph and MCP server connection.
This top-level graph calls them via their public generate_response() interfaces,
fans out concurrently, then hands results to the Memo Writer for synthesis.

Public API
----------
    await initialize()               # call once at FastAPI lifespan startup
    await run_pipeline("QUBT")       # blocking — returns complete result dict
    async for event in stream_pipeline("QUBT"):   # streaming — for SSE endpoints
        ...
"""

import asyncio
from typing import Any, AsyncGenerator

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from agents import analyst_agent, earnings_agent, sec_agent, news_agent, tech_agent
from agents import memo_writer


# ---------------------------------------------------------------------------
# Pipeline state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict):
    """Shared state flowing through the top-level pipeline graph."""

    ticker: str

    # Specialist agent outputs — empty string until the agent completes
    sec_analysis:      str
    earnings_analysis: str
    analyst_analysis:  str
    news_analysis:     str
    tech_analysis:     str

    # Agents that have finished (populated by orchestrator for observability)
    completed_agents: list[str]

    # Final output from Memo Writer
    memo: str
    date: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def orchestrator_node(state: PipelineState, config: RunnableConfig) -> dict:
    """
    Fan out to all 5 specialist agents in parallel.

    Each agent runs concurrently via asyncio.gather. As each one finishes it
    fires the optional `on_agent_complete` callback (used by stream_pipeline
    to push SSE progress events in real time, before gather returns).

    Errors are caught per-agent so one failure does not abort the whole pipeline.
    """
    ticker = state["ticker"]

    # Optional progress hook injected by stream_pipeline via RunnableConfig
    on_agent_complete = (config.get("configurable") or {}).get("on_agent_complete")

    async def _run(agent_module, agent_name: str, query: str) -> tuple[str, str]:
        try:
            result = await agent_module.generate_response(query)
            text = result["text"]
        except Exception as exc:
            # Degrade gracefully — Memo Writer will note insufficient data
            text = f"[{agent_name} agent unavailable: {exc}]"

        if on_agent_complete:
            await on_agent_complete(agent_name)

        return agent_name, text

    pairs = await asyncio.gather(
        _run(sec_agent,      "sec",      f"Analyse {ticker} SEC filings, cash position, dilution risk, and material 8-K events"),
        _run(earnings_agent, "earnings", f"Analyse {ticker} EPS trends, beat/miss history, revenue trajectory, and next earnings date"),
        _run(analyst_agent,  "analyst",  f"Analyse {ticker} valuation, financials, Wall Street consensus, and price targets"),
        _run(news_agent,     "news",     f"Analyse recent {ticker} news sentiment, coverage spikes, and sector developments"),
        _run(tech_agent,     "tech",     f"Analyse {ticker} research papers, publication velocity, and technology positioning"),
    )

    key_map = {
        "sec":      "sec_analysis",
        "earnings": "earnings_analysis",
        "analyst":  "analyst_analysis",
        "news":     "news_analysis",
        "tech":     "tech_analysis",
    }

    updates: dict[str, Any] = {"completed_agents": []}
    for name, text in pairs:
        updates[key_map[name]] = text
        updates["completed_agents"].append(name)

    return updates


async def memo_writer_node(state: PipelineState, config: RunnableConfig) -> dict:
    """
    Synthesise the five analyses into a structured investment memo.
    Single LLM call — no tools, no loop.
    """
    on_agent_complete = (config.get("configurable") or {}).get("on_agent_complete")

    result = await memo_writer.generate_memo(
        ticker=state["ticker"],
        sec_analysis=state["sec_analysis"],
        earnings_analysis=state["earnings_analysis"],
        analyst_analysis=state["analyst_analysis"],
        news_analysis=state["news_analysis"],
        tech_analysis=state["tech_analysis"],
    )

    if on_agent_complete:
        await on_agent_complete("memo_writer")

    return {
        "memo": result["memo"],
        "date": result["date"],
    }


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def _build_graph():
    """
    Compile the pipeline graph.

    No checkpointer — memo generation is a one-shot run, not a conversation.
    The individual specialist agents manage their own MemorySaver instances.
    """
    builder = StateGraph(PipelineState)

    builder.add_node("orchestrator",  orchestrator_node)
    builder.add_node("memo_writer",   memo_writer_node)

    builder.add_edge(START,          "orchestrator")
    builder.add_edge("orchestrator", "memo_writer")
    builder.add_edge("memo_writer",   END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_pipeline = None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def initialize() -> None:
    """
    Initialise all specialist agents and compile the pipeline graph.

    Call once at FastAPI lifespan startup (all 5 agent MCP subprocesses
    are started concurrently so startup latency is the slowest agent, not the sum).
    """
    global _pipeline

    if _pipeline is not None:
        return  # Already initialised

    # Boot all MCP subprocesses in parallel.
    # return_exceptions=True prevents one agent's failure from cancelling
    # the others mid-flight (which can surface as confusing secondary errors).
    results = await asyncio.gather(
        sec_agent.initialize(),
        earnings_agent.initialize(),
        analyst_agent.initialize(),
        news_agent.initialize(),
        tech_agent.initialize(),
        return_exceptions=True,
    )
    errors = [r for r in results if isinstance(r, BaseException)]
    if errors:
        raise errors[0]

    _pipeline = _build_graph()


async def run_pipeline(ticker: str) -> dict[str, Any]:
    """
    Run the full pipeline and return when the memo is complete.

    Best for CLI testing and background Celery tasks.
    For HTTP/SSE use stream_pipeline() to get real-time progress.

    Returns:
        {
            "ticker":            str,
            "memo":              str,   # full markdown investment memo
            "date":              str,   # ISO date YYYY-MM-DD
            "sec_analysis":      str,
            "earnings_analysis": str,
            "analyst_analysis":  str,
            "news_analysis":     str,
            "tech_analysis":     str,
            "completed_agents":  list[str],
        }
    """
    if _pipeline is None:
        raise RuntimeError("Pipeline not initialised — call initialize() first.")

    result = await _pipeline.ainvoke(_initial_state(ticker))
    return result


async def stream_pipeline(ticker: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run the pipeline and yield progress events as each agent completes.

    Designed to back an SSE endpoint — the caller converts each yielded dict
    into a ``data: <json>\\n\\n`` SSE frame.

    Yields
    ------
    Progress events (one per agent, fired as each finishes — not all at once):
        {"event": "agent_complete", "agent": "sec"}
        {"event": "agent_complete", "agent": "earnings"}
        {"event": "agent_complete", "agent": "analyst"}
        {"event": "agent_complete", "agent": "news"}
        {"event": "agent_complete", "agent": "tech"}
        {"event": "agent_complete", "agent": "memo_writer"}

    Final event (after memo_writer finishes):
        {
            "event":  "memo_complete",
            "ticker": "QUBT",
            "memo":   "## QUBT — Investment Memo\\n...",
            "date":   "2025-06-08",
        }

    Error event (if the pipeline throws):
        {"event": "error", "message": "..."}
    """
    if _pipeline is None:
        raise RuntimeError("Pipeline not initialised — call initialize() first.")

    pipeline = _pipeline
    ticker = ticker.strip().upper()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def _on_agent_complete(agent_name: str) -> None:
        """Callback fired inside each agent node as it finishes."""
        await queue.put({"event": "agent_complete", "agent": agent_name})

    async def _run() -> None:
        try:
            result = await pipeline.ainvoke(
                _initial_state(ticker),
                config={"configurable": {"on_agent_complete": _on_agent_complete}},
            )
            await queue.put({
                "event":  "memo_complete",
                "ticker": ticker,
                "memo":   result["memo"],
                "date":   result["date"],
            })
        except Exception as exc:
            await queue.put({"event": "error", "message": str(exc)})
        finally:
            await queue.put(None)  # sentinel — tells the generator to stop

    task = asyncio.create_task(_run())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        # Clean up if the client disconnects mid-stream
        if not task.done():
            task.cancel()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initial_state(ticker: str) -> PipelineState:
    """Return a blank PipelineState for a given ticker."""
    return {
        "ticker":            ticker.strip().upper(),
        "sec_analysis":      "",
        "earnings_analysis": "",
        "analyst_analysis":  "",
        "news_analysis":     "",
        "tech_analysis":     "",
        "completed_agents":  [],
        "memo":              "",
        "date":              "",
    }


# ---------------------------------------------------------------------------
# Dev CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _main() -> None:
        ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "QUBT"
        print(f"Initialising pipeline…")
        await initialize()

        print(f"Running pipeline for {ticker}…\n")
        async for event in stream_pipeline(ticker):
            if event["event"] == "agent_complete":
                print(f"  ✓  {event['agent']} agent complete")
            elif event["event"] == "memo_complete":
                print(f"\n{'=' * 60}")
                print(event["memo"])
                print(f"{'=' * 60}")
            elif event["event"] == "error":
                print(f"  ✗  Pipeline error: {event['message']}", file=sys.stderr)

    asyncio.run(_main())
