"""
Finance MCP Server
Provides stock price, fundamentals, earnings, and financial ratios
via yfinance (free, no API key required).
"""

from typing import Any, cast
import logging
import pandas as pd
import yfinance as yf
from fastmcp import FastMCP, Context
import json

mcp = FastMCP("finance-mcp")
logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 500) -> str:
    """Truncate at the last sentence end within limit, falling back to last word boundary."""
    if len(text) <= limit:
        return text
    chunk = text[:limit]
    sentence_end = max(chunk.rfind(". "), chunk.rfind("! "), chunk.rfind("? "))
    if sentence_end != -1:
        return chunk[: sentence_end + 1]
    word_end = chunk.rfind(" ")
    return chunk[:word_end] + "…" if word_end != -1 else chunk


def _safe(val: Any) -> Any:
    """Convert non-JSON-serialisable values (NaN, Inf, Timestamps) to safe types."""
    import math
    import pandas as pd

    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    return val


def _clean_dict(d: dict) -> dict:
    return {k: _safe(v) for k, v in d.items() if _safe(v) is not None}


@mcp.tool()
async def get_stock_info(ticker: str, ctx: Context) -> dict[str, Any]:
    """
    Get current stock price, market cap, volume, and key company metadata.
    Fast call — uses yfinance fast_info for minimal latency.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    t = yf.Ticker(ticker.upper())
    info = t.info
    fast = t.fast_info

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "exchange": info.get("exchange", ""),
        "currency": info.get("currency", "USD"),
        "price": {
            "current": _safe(fast.last_price),
            "previous_close": _safe(fast.previous_close),
            "open": _safe(fast.open),
            "day_high": _safe(fast.day_high),
            "day_low": _safe(fast.day_low),
            "fifty_two_week_high": _safe(fast.year_high),
            "fifty_two_week_low": _safe(fast.year_low),
        },
        "volume": {
            "current": _safe(fast.last_volume),
            "three_month_avg": _safe(info.get("averageVolume3Month")),
        },
        "market_cap": _safe(fast.market_cap),
        "shares_outstanding": _safe(fast.shares),
        "description": _truncate(info.get("longBusinessSummary", "")),
    }


@mcp.tool()
def get_financials(ticker: str) -> dict[str, Any]:
    """
    Get annual income statement, balance sheet, and cash flow data.
    Returns most recent 2 years for trend analysis.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    t = yf.Ticker(ticker.upper())

    def _df_to_dict(df):
        if df is None or df.empty:
            return {}
        # Limit to 2 most recent periods and key rows
        df = df.iloc[:, :2]
        return {
            str(col.date()): {
                str(idx): _safe(val)
                for idx, val in col_data.items()
                if _safe(val) is not None
            }
            for col, col_data in df.items()
        }

    income = t.financials
    balance = t.balance_sheet
    cashflow = t.cashflow

    # Pull key metrics for quick agent consumption
    info = t.info
    return {
        "ticker": ticker.upper(),
        "key_metrics": _clean_dict({
            "revenue_ttm": info.get("totalRevenue"),
            "gross_profit": info.get("grossProfits"),
            "ebitda": info.get("ebitda"),
            "net_income": info.get("netIncomeToCommon"),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "free_cashflow": info.get("freeCashflow"),
            "operating_cashflow": info.get("operatingCashflow"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margins": info.get("profitMargins"),
            "gross_margins": info.get("grossMargins"),
        }),
        "valuation": _clean_dict({
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "price_to_book": info.get("priceToBook"),
            "enterprise_value": info.get("enterpriseValue"),
            "ev_to_revenue": info.get("enterpriseToRevenue"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
        }),
        "income_statement": _df_to_dict(income),
        "balance_sheet": _df_to_dict(balance),
        "cash_flow": _df_to_dict(cashflow),
    }


@mcp.tool()
def get_earnings(ticker: str) -> dict[str, Any]:
    """
    Get earnings history and upcoming earnings date.
    Returns EPS estimates vs actuals, surprise percentages, and next earnings date.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    t = yf.Ticker(ticker.upper())
    info = t.info

    # Quarterly earnings history
    earnings_hist = t.earnings_history
    history = []
    if earnings_hist is not None and not earnings_hist.empty:
        for _, row in earnings_hist.tail(8).iterrows():
            history.append({
                "quarter": str(row.get("quarter", "")),
                "eps_estimate": _safe(row.get("epsestimate")),
                "eps_actual": _safe(row.get("epsactual")),
                "surprise_pct": _safe(row.get("epssurprisepct")),
            })

    return {
        "ticker": ticker.upper(),
        "next_earnings_date": str(info.get("earningsTimestamp", "")),
        "next_earnings_date_start": str(info.get("earningsTimestampStart", "")),
        "next_earnings_date_end": str(info.get("earningsTimestampEnd", "")),
        "forward_eps": _safe(info.get("forwardEps")),
        "trailing_eps": _safe(info.get("trailingEps")),
        "earnings_quarterly_growth": _safe(info.get("earningsQuarterlyGrowth")),
        "earnings_history": history,
    }


@mcp.tool()
def get_analyst_recommendations(ticker: str) -> dict[str, Any]:
    """
    Get analyst price targets and buy/sell/hold ratings distribution.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    t = yf.Ticker(ticker.upper())
    info = t.info

    recs = t.recommendations
    recent_recs = []
    if isinstance(recs, pd.DataFrame) and not recs.empty:
        for _, row in recs.tail(10).iterrows():
            recent_recs.append({
                "firm": row.get("Firm", ""),
                "to_grade": row.get("To Grade", ""),
                "from_grade": row.get("From Grade", ""),
                "action": row.get("Action", ""),
            })

    return {
        "ticker": ticker.upper(),
        "target_price": {
            "mean": _safe(info.get("targetMeanPrice")),
            "high": _safe(info.get("targetHighPrice")),
            "low": _safe(info.get("targetLowPrice")),
            "median": _safe(info.get("targetMedianPrice")),
            "analyst_count": info.get("numberOfAnalystOpinions"),
        },
        "recommendation": {
            "mean": _safe(info.get("recommendationMean")),
            "key": info.get("recommendationKey", ""),
        },
        "recent_ratings": recent_recs,
    }


@mcp.tool()
def get_price_history(ticker: str, period: str = "6mo") -> dict[str, Any]:
    """
    Get historical price data for chart rendering.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
        period: Time period — '1mo', '3mo', '6mo', '1y', '2y', '5y'
    """
    t = yf.Ticker(ticker.upper())
    hist = t.history(period=period, interval="1d")

    if hist.empty:
        return {"ticker": ticker.upper(), "period": period, "data": []}

    data = []
    for date, row in hist.iterrows():
        data.append({
            "date": cast(pd.Timestamp, date).strftime("%Y-%m-%d"),
            "open": round(_safe(row["Open"]) or 0, 2),
            "high": round(_safe(row["High"]) or 0, 2),
            "low": round(_safe(row["Low"]) or 0, 2),
            "close": round(_safe(row["Close"]) or 0, 2),
            "volume": int(_safe(row["Volume"]) or 0),
        })

    return {
        "ticker": ticker.upper(),
        "period": period,
        "data_points": len(data),
        "data": data,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
