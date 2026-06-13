"""
Chat route
POST /api/v1/chat  →  single-turn chat message routed to the appropriate specialist agent.

Requires authentication — valid Supabase JWT in the Authorization header.

Memory is thread-based: pass back the returned ``thread_id`` on subsequent
requests to continue the same conversation.
"""

from fastapi import APIRouter, HTTPException

from agents import analyst_agent, earnings_agent, sec_agent, news_agent, research_agent
from api.dependencies import CurrentUser
from api.schemas.memo import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

_AGENT_MAP = {
    "analyst":  analyst_agent,
    "earnings": earnings_agent,
    "sec":      sec_agent,
    "news":     news_agent,
    "research": research_agent,
}


@router.post("", response_model=ChatResponse, summary="Chat with a specialist agent — requires auth")
async def chat(request: ChatRequest, user: CurrentUser) -> ChatResponse:
    """
    Route a user message to the appropriate specialist agent and return the response.

    Requires: ``Authorization: Bearer <supabase_access_token>``

    **Routing guide:**
    - `analyst`  — valuation, price targets, financials, chart patterns
    - `earnings` — EPS history, beat/miss streaks, next earnings date
    - `sec`      — SEC filings, cash runway, dilution risk, 8-K events
    - `news`     — recent headlines, sentiment, sector news
    - `research` — research papers, technology positioning
    """
    agent_module = _AGENT_MAP.get(request.agent)
    if agent_module is None:
        raise HTTPException(status_code=400, detail=f"Unknown agent: '{request.agent}'")

    query = f"[{request.ticker.upper()}] {request.message}"

    try:
        result = await agent_module.generate_response(
            query=query,
            thread_id=request.thread_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ChatResponse(
        text=result["text"],
        thread_id=result["thread_id"],
        agent=request.agent,
    )
