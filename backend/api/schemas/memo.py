"""
Pydantic schemas for the Quanta Terminal API.
"""

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

class StockQuote(BaseModel):
    ticker: str
    name: str
    price: float | None
    change_pct: float | None          # % change from previous close
    market_cap: float | None          # in USD
    volume: int | None


class StocksResponse(BaseModel):
    stocks: list[StockQuote]


# ---------------------------------------------------------------------------
# Memo generation — SSE event shapes
# ---------------------------------------------------------------------------

class AgentCompleteEvent(BaseModel):
    event: Literal["agent_complete"] = "agent_complete"
    agent: str                         # "sec" | "earnings" | "analyst" | "news" | "tech" | "memo_writer"
    label: str                         # human-readable agent name


class MemoCompleteEvent(BaseModel):
    event: Literal["memo_complete"] = "memo_complete"
    ticker: str
    memo: str                          # full markdown investment memo
    date: str                          # ISO YYYY-MM-DD


class PipelineErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    message: str


# ---------------------------------------------------------------------------
# Memo lookup (Phase 3: Supabase-backed)
# ---------------------------------------------------------------------------

class MemoRecord(BaseModel):
    ticker: str
    memo: str
    date: str
    sec_analysis: str = ""
    earnings_analysis: str = ""
    analyst_analysis: str = ""
    news_analysis: str = ""
    tech_analysis: str = ""


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker, e.g. QUBT")
    message: str = Field(..., min_length=1)
    thread_id: str | None = Field(
        default=None,
        description="Omit to start a new conversation; pass back to continue one.",
    )
    agent: Literal["analyst", "earnings", "sec", "news", "tech"] = Field(
        default="analyst",
        description="Which specialist agent to route this message to.",
    )


class ChatResponse(BaseModel):
    text: str
    thread_id: str                     # always returned so the client can continue the thread
    agent: str
