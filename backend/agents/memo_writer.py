"""
Memo Writer
Synthesis node — NOT a ReAct agent. Takes the outputs of all 5 specialist agents
and makes a single LLM call to produce a structured investment memo.

No tools. No loop. One call → one memo.
"""

from datetime import date
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model

from prompts.system_prompts import memo_writer_system_prompt
from core.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _build_synthesis_prompt(
    ticker: str,
    sec_analysis: str,
    earnings_analysis: str,
    analyst_analysis: str,
    news_analysis: str,
    tech_analysis: str,
) -> str:
    """Assemble the five agent outputs into a single prompt for the memo writer."""
    today = date.today().strftime("%B %d, %Y")
    return f"""Today's date: {today}
Ticker: {ticker}

You have received the following specialist analyses. Synthesise them into a structured investment memo.

---
### SEC ANALYSIS
{sec_analysis}

---
### EARNINGS ANALYSIS
{earnings_analysis}

---
### ANALYST / VALUATION ANALYSIS
{analyst_analysis}

---
### NEWS ANALYSIS
{news_analysis}

---
### TECHNOLOGY ANALYSIS
{tech_analysis}

---

Now write the investment memo following the exact structure in your instructions."""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def generate_memo(
    ticker: str,
    sec_analysis: str,
    earnings_analysis: str,
    analyst_analysis: str,
    news_analysis: str,
    tech_analysis: str,
) -> dict[str, Any]:
    """
    Synthesise five specialist analyses into a structured investment memo.

    Args:
        ticker:            Stock ticker (e.g. "QUBT")
        sec_analysis:      Output text from sec_agent.generate_response()
        earnings_analysis: Output text from earnings_agent.generate_response()
        analyst_analysis:  Output text from analyst_agent.generate_response()
        news_analysis:     Output text from news_agent.generate_response()
        tech_analysis:     Output text from tech_agent.generate_response()

    Returns:
        {
            "ticker": str  — the ticker this memo covers,
            "memo":   str  — the full markdown investment memo,
            "date":   str  — ISO date string (YYYY-MM-DD),
        }
    """
    model = _build_model()

    system = SystemMessage(content=memo_writer_system_prompt)
    human = HumanMessage(
        content=_build_synthesis_prompt(
            ticker=ticker,
            sec_analysis=sec_analysis,
            earnings_analysis=earnings_analysis,
            analyst_analysis=analyst_analysis,
            news_analysis=news_analysis,
            tech_analysis=tech_analysis,
        )
    )

    response = await model.ainvoke([system, human])

    return {
        "ticker": ticker,
        "memo": response.content,
        "date": date.today().isoformat(),
    }
