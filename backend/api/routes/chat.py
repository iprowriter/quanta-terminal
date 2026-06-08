"""
Chat route
POST /api/chat  →  single-turn chat message routed to the appropriate specialist agent.

Memory is thread-based: pass back the returned ``thread_id`` on subsequent
requests to continue the same conversation.
"""

from fastapi import APIRouter, HTTPException

from agents import analyst_agent, earnings_agent, sec_agent, news_agent, tech_agent
from api.schemas.memo import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# Map agent name → module with a generate_response(query, thread_id) interface
_AGENT_MAP = {
    "analyst":  analyst_agent,
    "earnings": earnings_agent,
    "sec":      sec_agent,
    "news":     news_agent,
    "tech":     tech_agent,
}


@router.post("", response_model=ChatResponse, summary="Chat with a specialist agent")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Route a user message to the appropriate specialist agent and return the response.

    The ``agent`` field defaults to ``"analyst"`` — the broadest agent with access
    to price, financials, recommendations, and price history.

    Pass the returned ``thread_id`` on the next request to continue the same
    conversation. The agent remembers the full message history for that thread.

    **Routing guide:**
    - `analyst`  — valuation, price targets, financials, chart patterns
    - `earnings` — EPS history, beat/miss streaks, next earnings date
    - `sec`      — SEC filings, cash runway, dilution risk, 8-K events
    - `news`     — recent headlines, sentiment, sector news
    - `tech`     — research papers, technology positioning
    """
    agent_name = request.agent
    agent_module = _AGENT_MAP.get(agent_name)

    if agent_module is None:
        raise HTTPException(status_code=400, detail=f"Unknown agent: '{agent_name}'")

    # Prefix the message with the ticker so the agent has context
    # even on follow-up turns where the user may not repeat it
    query = f"[{request.ticker.upper()}] {request.message}"

    try:
        result = await agent_module.generate_response(
            query=query,
            thread_id=request.thread_id,
        )
    except RuntimeError as exc:
        # Agent not initialised — shouldn't happen after lifespan startup
        raise HTTPException(status_code=503, detail=str(exc))

    return ChatResponse(
        text=result["text"],
        thread_id=result["thread_id"],
        agent=agent_name,
    )
