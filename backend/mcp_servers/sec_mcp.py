"""
SEC EDGAR MCP Server
Provides tools for fetching and parsing SEC filings for tracked stocks.
Uses the free SEC EDGAR REST API — no API key required.
"""

import httpx
import re
from typing import Any
from fastmcp import FastMCP
from bs4 import BeautifulSoup

mcp = FastMCP("sec-mcp")

EDGAR_BASE = "https://data.sec.gov"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
HEADERS = {
    # SEC requires a descriptive User-Agent per their fair access policy
    "User-Agent": "Quanta Terminal research@quantaterminal.com",
    "Accept": "application/json",
}

# Map ticker → CIK (SEC's internal company ID)
# Cached in-process; refreshed on first call per server start
_cik_cache: dict[str, str] = {}


async def _get_cik(ticker: str) -> str:
    """Resolve a ticker symbol to its SEC CIK number."""
    ticker = ticker.upper()
    if ticker in _cik_cache:
        return _cik_cache[ticker]

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get("https://www.sec.gov/files/company_tickers.json")
        resp.raise_for_status()
        # Returns { "0": {"cik_str": 123, "ticker": "AAPL", ...}, ... }
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker:
                cik = str(entry["cik_str"])
                _cik_cache[ticker] = cik
                return cik

    raise ValueError(f"Could not resolve CIK for ticker: {ticker}")


async def _get_submissions(cik: str) -> dict:
    """Fetch the submissions JSON for a company — contains all filing history."""
    padded_cik = cik.zfill(10)
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        resp = await client.get(f"{EDGAR_BASE}/submissions/CIK{padded_cik}.json")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_company_info(ticker: str) -> dict[str, Any]:
    """
    Get basic company information from SEC EDGAR for a given ticker.
    Returns company name, SIC code, state of incorporation, and fiscal year end.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    cik = await _get_cik(ticker)
    data = await _get_submissions(cik)
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "name": data.get("name", ""),
        "sic": data.get("sic", ""),
        "sic_description": data.get("sicDescription", ""),
        "state_of_incorporation": data.get("stateOfIncorporation", ""),
        "fiscal_year_end": data.get("fiscalYearEnd", ""),
        "business_address": data.get("addresses", {}).get("business", {}),
    }


@mcp.tool()
async def search_filings(
    ticker: str,
    filing_type: str = "10-K",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Search for SEC filings by ticker and filing type.
    Returns a list of recent filings with accession numbers and dates.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
        filing_type: SEC form type — '10-K', '10-Q', '8-K', 'S-1', etc.
        limit: Number of filings to return (default 5, max 20)
    """
    limit = min(limit, 20)
    cik = await _get_cik(ticker)
    data = await _get_submissions(cik)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    descriptions = recent.get("primaryDocument", [])
    report_dates = recent.get("reportDate", [])

    results = []
    for i, form in enumerate(forms):
        if form.upper() == filing_type.upper():
            accession = accessions[i].replace("-", "")
            results.append(
                {
                    "ticker": ticker.upper(),
                    "cik": cik,
                    "form_type": form,
                    "filing_date": dates[i] if i < len(dates) else "",
                    "report_date": report_dates[i] if i < len(report_dates) else "",
                    "accession_number": accessions[i],
                    "primary_document": descriptions[i] if i < len(descriptions) else "",
                    "filing_url": (
                        f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
                        f"{descriptions[i] if i < len(descriptions) else ''}"
                    ),
                    "index_url": (
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                        f"&CIK={cik}&type={filing_type}&dateb=&owner=include&count=40"
                    ),
                }
            )
        if len(results) >= limit:
            break

    return results


@mcp.tool()
async def get_filing_text(
    ticker: str,
    filing_type: str = "10-K",
    max_chars: int = 8000,
) -> dict[str, Any]:
    """
    Fetch and parse the text content of the most recent filing of a given type.
    Strips HTML and returns clean text, truncated to max_chars for token efficiency.
    Ideal for feeding into the SEC agent for risk factor and financial analysis.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
        filing_type: SEC form type — '10-K', '10-Q', or '8-K'
        max_chars: Maximum characters to return (default 8000 to control token usage)
    """
    filings = await search_filings(ticker, filing_type, limit=1)
    if not filings:
        return {"error": f"No {filing_type} filings found for {ticker}"}

    filing = filings[0]
    url = filing["filing_url"]

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    # Strip HTML tags and clean up whitespace
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    text = text[:max_chars]

    return {
        "ticker": ticker.upper(),
        "form_type": filing_type,
        "filing_date": filing["filing_date"],
        "report_date": filing["report_date"],
        "source_url": url,
        "text": text,
        "char_count": len(text),
        "truncated": len(text) == max_chars,
    }


@mcp.tool()
async def get_company_facts(ticker: str) -> dict[str, Any]:
    """
    Fetch structured financial facts from SEC XBRL data.
    Returns key financial metrics: revenue, net income, assets, liabilities, shares outstanding.
    This is structured data — more reliable than parsing filing text.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
    """
    cik = await _get_cik(ticker)
    padded_cik = cik.zfill(10)

    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        resp = await client.get(f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{padded_cik}.json")
        resp.raise_for_status()
        facts = resp.json()

    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def _latest(concept: str) -> dict | None:
        """Pull the most recent annual value for a GAAP concept."""
        data = us_gaap.get(concept, {}).get("units", {})
        usd = data.get("USD", [])
        annual = [e for e in usd if e.get("form") in ("10-K", "10-K/A") and e.get("val") is not None]
        if not annual:
            return None
        latest = sorted(annual, key=lambda x: x.get("end", ""), reverse=True)[0]
        return {"value": latest["val"], "period_end": latest.get("end", ""), "unit": "USD"}

    def _latest_shares() -> dict | None:
        shares = us_gaap.get("CommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
        if not shares:
            return None
        latest = sorted(shares, key=lambda x: x.get("end", ""), reverse=True)[0]
        return {"value": latest["val"], "period_end": latest.get("end", ""), "unit": "shares"}

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company_name": facts.get("entityName", ""),
        "financials": {
            "revenue": _latest("Revenues") or _latest("RevenueFromContractWithCustomerExcludingAssessedTax"),
            "net_income": _latest("NetIncomeLoss"),
            "total_assets": _latest("Assets"),
            "total_liabilities": _latest("Liabilities"),
            "cash_and_equivalents": _latest("CashAndCashEquivalentsAtCarryingValue"),
            "shares_outstanding": _latest_shares(),
            "research_and_development": _latest("ResearchAndDevelopmentExpense"),
            "operating_expenses": _latest("OperatingExpenses"),
        },
    }


@mcp.tool()
async def get_recent_8k_events(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Fetch recent 8-K filings (material events) for a company.
    8-Ks cover earnings releases, acquisitions, partnerships, leadership changes, etc.
    Returns filing metadata + first 2000 chars of each filing.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT')
        limit: Number of recent 8-Ks to return (default 5)
    """
    filings = await search_filings(ticker, "8-K", limit=limit)
    results = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for filing in filings:
            try:
                resp = await client.get(filing["filing_url"])
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                for tag in soup(["script", "style"]):
                    tag.decompose()
                text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
                snippet = text[:2000]
            except Exception:
                snippet = ""

            results.append(
                {
                    "ticker": ticker.upper(),
                    "form_type": "8-K",
                    "filing_date": filing["filing_date"],
                    "filing_url": filing["filing_url"],
                    "snippet": snippet,
                }
            )

    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
