"""
News MCP Server
Fetches and scores news articles for tracked stocks using NewsAPI (free tier)
with RSS feeds as fallback. Includes lightweight sentiment scoring.
"""

import re
import httpx
import feedparser
from datetime import datetime, timedelta, timezone
from typing import Any
from fastmcp import FastMCP
from core.config import settings

mcp = FastMCP("news-mcp")

NEWS_API_BASE = "https://newsapi.org/v2"

# Lightweight keyword-based sentiment — no model needed, fast and interpretable
POSITIVE_WORDS = {
    "partnership", "contract", "milestone", "breakthrough", "award", "revenue",
    "growth", "profit", "upgrade", "buy", "outperform", "bullish", "strong",
    "record", "expand", "launch", "approval", "wins", "beats", "exceeds",
    "innovation", "commercialization", "deal", "collaboration", "investment",
}
NEGATIVE_WORDS = {
    "downgrade", "sell", "underperform", "bearish", "loss", "deficit", "delay",
    "risk", "lawsuit", "investigation", "fraud", "miss", "below", "cut", "weak",
    "dilution", "offering", "burn", "concern", "warning", "decline", "drop",
    "disappointing", "volatile", "short", "squeeze",
}

# RSS feeds relevant to quantum computing and AI chip stocks
RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://www.theregister.com/headlines.atom",
]


def _score_sentiment(text: str) -> dict[str, Any]:
    """
    Score sentiment of a text using keyword matching.
    Returns a score from -1.0 (very negative) to +1.0 (very positive).
    """
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos_hits = words & POSITIVE_WORDS
    neg_hits = words & NEGATIVE_WORDS
    total = len(pos_hits) + len(neg_hits)

    if total == 0:
        score = 0.0
        label = "neutral"
    else:
        score = round((len(pos_hits) - len(neg_hits)) / total, 2)
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"

    return {
        "score": score,
        "label": label,
        "positive_signals": list(pos_hits),
        "negative_signals": list(neg_hits),
    }


@mcp.tool()
async def search_news(
    ticker: str,
    company_name: str = "",
    days_back: int = 7,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search for recent news articles about a stock using NewsAPI.
    Falls back to RSS feeds if no API key is configured.
    Returns articles with sentiment scores.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
        company_name: Full company name to broaden search (e.g. 'Quantum Computing Inc')
        days_back: How many days back to search (default 7, max 30 on free tier)
        limit: Max articles to return (default 10)
    """
    api_key = settings.news_api_key
    query = f"{ticker} OR {company_name}" if company_name else ticker
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    articles = []

    if api_key:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": min(limit, 100),
                    "apiKey": api_key,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for a in data.get("articles", [])[:limit]:
                    text = f"{a.get('title', '')} {a.get('description', '')}"
                    sentiment = _score_sentiment(text)
                    articles.append({
                        "title": a.get("title", ""),
                        "description": a.get("description", ""),
                        "source": a.get("source", {}).get("name", ""),
                        "url": a.get("url", ""),
                        "published_at": a.get("publishedAt", ""),
                        "sentiment": sentiment,
                    })

    # RSS fallback or supplement
    if not articles:
        articles = await _fetch_rss_news(ticker, limit)

    # Aggregate sentiment stats
    labels = [a["sentiment"]["label"] for a in articles]
    return {
        "ticker": ticker.upper(),
        "query": query,
        "date_range": f"Last {days_back} days",
        "total_articles": len(articles),
        "sentiment_summary": {
            "positive": labels.count("positive"),
            "neutral": labels.count("neutral"),
            "negative": labels.count("negative"),
            "overall_score": round(
                sum(a["sentiment"]["score"] for a in articles) / len(articles), 2
            ) if articles else 0.0,
        },
        "articles": articles,
    }


async def _fetch_rss_news(ticker: str, limit: int) -> list[dict]:
    """Fallback RSS news fetch — relevant for finance news when NewsAPI key is absent."""
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = str(entry.get("title", ""))
                summary = str(entry.get("summary", ""))
                if ticker.upper() in (title + summary).upper():
                    text = f"{title} {summary}"
                    sentiment = _score_sentiment(text)
                    articles.append({
                        "title": title,
                        "description": summary[:200],
                        "source": str(getattr(feed, "feed", {}).get("title", feed_url)),
                        "url": entry.get("link", ""),
                        "published_at": entry.get("published", ""),
                        "sentiment": sentiment,
                    })
                    if len(articles) >= limit:
                        return articles
        except Exception:
            continue
    return articles


@mcp.tool()
async def detect_news_spike(
    ticker: str,
    company_name: str = "",
    spike_threshold: int = 5,
) -> dict[str, Any]:
    """
    Detect if there is an unusual spike in news volume for a stock.
    Compares articles in the last 24h vs the prior 7-day average.
    Used by the alerts system to trigger memo re-runs.

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name for broader search
        spike_threshold: Minimum articles in 24h to flag as a spike (default 5)
    """
    recent = await search_news(ticker, company_name, days_back=1, limit=20)
    baseline = await search_news(ticker, company_name, days_back=7, limit=50)

    recent_count = recent["total_articles"]
    baseline_daily_avg = round(baseline["total_articles"] / 7, 1)
    is_spike = recent_count >= spike_threshold

    return {
        "ticker": ticker.upper(),
        "is_spike": is_spike,
        "articles_last_24h": recent_count,
        "daily_avg_last_7d": baseline_daily_avg,
        "spike_threshold": spike_threshold,
        "sentiment_24h": recent["sentiment_summary"],
        "top_articles": recent["articles"][:3],
    }


@mcp.tool()
async def get_sector_news(
    sector: str = "quantum computing",
    days_back: int = 3,
    limit: int = 8,
) -> dict[str, Any]:
    """
    Search for sector-level news (e.g. 'quantum computing', 'AI chips').
    Useful for the Tech Tracker tab and understanding macro tailwinds/headwinds.

    Args:
        sector: Topic or sector to search (e.g. 'quantum computing', 'AI semiconductors')
        days_back: How many days back to search
        limit: Max articles to return
    """
    api_key = settings.news_api_key
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    articles = []

    if api_key:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    "q": sector,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": min(limit, 100),
                    "apiKey": api_key,
                },
            )
            if resp.status_code == 200:
                for a in resp.json().get("articles", [])[:limit]:
                    text = f"{a.get('title', '')} {a.get('description', '')}"
                    articles.append({
                        "title": a.get("title", ""),
                        "description": a.get("description", ""),
                        "source": a.get("source", {}).get("name", ""),
                        "url": a.get("url", ""),
                        "published_at": a.get("publishedAt", ""),
                        "sentiment": _score_sentiment(text),
                    })

    return {
        "sector": sector,
        "date_range": f"Last {days_back} days",
        "total_articles": len(articles),
        "articles": articles,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
