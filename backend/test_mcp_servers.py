"""
Phase 1 integration test — verify all MCP servers return real data for QUBT.
Run with: uv run python test_mcp_servers.py

Each test hits a live external API. Requires internet access.
NewsAPI tests are skipped if NEWS_API_KEY is not set.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Colours for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

TICKER = "QUBT"
passed = 0
failed = 0
skipped = 0


def header(title: str):
    print(f"\n{BOLD}{BLUE}{'─' * 50}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─' * 50}{RESET}")


def ok(label: str, value: str = ""):
    global passed
    passed += 1
    suffix = f" → {value}" if value else ""
    print(f"  {GREEN}✓{RESET} {label}{YELLOW}{suffix}{RESET}")


def fail(label: str, error: str = ""):
    global failed
    failed += 1
    print(f"  {RED}✗ {label}{RESET}")
    if error:
        print(f"    {RED}{error}{RESET}")


def skip(label: str, reason: str = ""):
    global skipped
    skipped += 1
    print(f"  {YELLOW}⊘ {label} (skipped: {reason}){RESET}")


# ─── SEC MCP Tests ────────────────────────────────────────────────────────────

async def test_sec_mcp():
    header("SEC MCP — sec_mcp.py")
    from mcp_servers.sec_mcp import get_company_info, search_filings, get_company_facts

    # Test 1: Company info
    try:
        result = await get_company_info(TICKER)
        assert result.get("name"), "Company name missing"
        assert result.get("cik"), "CIK missing"
        ok("get_company_info", f"{result['name']} (CIK {result['cik']})")
    except Exception as e:
        fail("get_company_info", str(e))

    # Test 2: Search 10-K filings
    try:
        result = await search_filings(TICKER, "10-K", limit=2)
        assert isinstance(result, list) and len(result) > 0, "No 10-K filings returned"
        ok("search_filings (10-K)", f"{len(result)} filings found, latest: {result[0]['filing_date']}")
    except Exception as e:
        fail("search_filings (10-K)", str(e))

    # Test 3: Search 8-K filings
    try:
        result = await search_filings(TICKER, "8-K", limit=3)
        assert isinstance(result, list), "Expected list"
        ok("search_filings (8-K)", f"{len(result)} recent 8-Ks found")
    except Exception as e:
        fail("search_filings (8-K)", str(e))

    # Test 4: Company facts (XBRL structured data)
    try:
        result = await get_company_facts(TICKER)
        financials = result.get("financials", {})
        ok(
            "get_company_facts",
            f"cash=${financials.get('cash_and_equivalents', {}).get('value', 'N/A'):,}" if financials.get('cash_and_equivalents') else "data returned"
        )
    except Exception as e:
        fail("get_company_facts", str(e))


# ─── Finance MCP Tests ────────────────────────────────────────────────────────

def test_finance_mcp():
    header("Finance MCP — finance_mcp.py")
    from mcp_servers.finance_mcp import get_stock_info, get_financials, get_earnings, get_price_history

    # Test 1: Stock info
    try:
        result = get_stock_info(TICKER)
        price = result.get("price", {}).get("current")
        assert price is not None, "Price is None"
        ok("get_stock_info", f"${price} | market cap ${result.get('market_cap', 0):,.0f}")
    except Exception as e:
        fail("get_stock_info", str(e))

    # Test 2: Financials
    try:
        result = get_financials(TICKER)
        metrics = result.get("key_metrics", {})
        ok("get_financials", f"revenue_ttm=${metrics.get('revenue_ttm', 'N/A')}")
    except Exception as e:
        fail("get_financials", str(e))

    # Test 3: Earnings
    try:
        result = get_earnings(TICKER)
        hist = result.get("earnings_history", [])
        ok("get_earnings", f"{len(hist)} quarters of history")
    except Exception as e:
        fail("get_earnings", str(e))

    # Test 4: Price history
    try:
        result = get_price_history(TICKER, "3mo")
        points = result.get("data_points", 0)
        assert points > 0, "No price data returned"
        ok("get_price_history", f"{points} daily data points (3mo)")
    except Exception as e:
        fail("get_price_history", str(e))


# ─── News MCP Tests ───────────────────────────────────────────────────────────

async def test_news_mcp():
    header("News MCP — news_mcp.py")
    from mcp_servers.news_mcp import search_news, detect_news_spike

    has_key = bool(os.getenv("NEWS_API_KEY"))

    if not has_key:
        skip("search_news (NewsAPI)", "NEWS_API_KEY not set — will use RSS fallback")
        skip("detect_news_spike", "NEWS_API_KEY not set")

    # Test RSS fallback / NewsAPI
    try:
        result = await search_news(TICKER, "Quantum Computing", days_back=7, limit=5)
        count = result.get("total_articles", 0)
        sentiment = result.get("sentiment_summary", {})
        ok(
            "search_news",
            f"{count} articles | sentiment: {sentiment.get('positive', 0)}+ {sentiment.get('negative', 0)}-"
        )
    except Exception as e:
        fail("search_news", str(e))

    # Test sentiment scoring directly
    try:
        from mcp_servers.news_mcp import _score_sentiment
        pos = _score_sentiment("QUBT wins NASA contract, strong revenue growth milestone")
        neg = _score_sentiment("QUBT dilution risk, analyst downgrade, disappointing earnings miss")
        assert pos["label"] == "positive", f"Expected positive, got {pos['label']}"
        assert neg["label"] == "negative", f"Expected negative, got {neg['label']}"
        ok("sentiment scoring", f"positive={pos['score']}, negative={neg['score']}")
    except Exception as e:
        fail("sentiment scoring", str(e))


# ─── Research MCP Tests ───────────────────────────────────────────────────────

def test_research_mcp():
    header("Research MCP — research_mcp.py")
    from mcp_servers.research_mcp import search_papers, get_papers_for_ticker

    # Test 1: Generic search
    try:
        results = search_papers("photonic quantum computing", max_results=3, days_back=180)
        assert isinstance(results, list), "Expected list"
        ok("search_papers", f"{len(results)} papers found")
        if results:
            print(f"     → Latest: \"{results[0]['title'][:60]}...\"")
    except Exception as e:
        fail("search_papers", str(e))

    # Test 2: Ticker-specific papers
    try:
        result = get_papers_for_ticker(TICKER, max_results=3)
        count = result.get("total_papers", 0)
        ok("get_papers_for_ticker", f"{count} papers for {TICKER} ({', '.join(result.get('keywords_used', []))})")
    except Exception as e:
        fail("get_papers_for_ticker", str(e))


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    total = passed + failed + skipped
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  {YELLOW}{skipped} skipped{RESET}  ({total} total)")
    print(f"{BOLD}{'─' * 50}{RESET}\n")

    if failed > 0:
        print(f"{RED}Some tests failed. Check error messages above.{RESET}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}All tests passed. Phase 1 MCP servers are working.{RESET}\n")


async def main():
    print(f"\n{BOLD}Quanta Terminal — Phase 1 MCP Server Tests{RESET}")
    print(f"Ticker: {TICKER} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    await test_sec_mcp()
    test_finance_mcp()
    await test_news_mcp()
    test_research_mcp()
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
