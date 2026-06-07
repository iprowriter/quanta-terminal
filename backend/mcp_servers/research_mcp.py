"""
Research MCP Server
Searches arXiv for academic papers relevant to quantum computing and AI chip stocks.
Uses the free arXiv API — no key required.
Powers the Tech Tracker tab and the Tech Agent in the memo pipeline.
"""

import arxiv
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from fastmcp import FastMCP

mcp = FastMCP("research-mcp")

# arXiv categories most relevant to the Quanta Terminal watchlist
RELEVANT_CATEGORIES = [
    "quant-ph",   # Quantum Physics (covers quantum computing)
    "cs.ET",      # Emerging Technologies
    "cs.AI",      # Artificial Intelligence
    "cond-mat.supr-con",  # Superconductivity (Rigetti, IBM)
]

# Company → research keywords mapping
COMPANY_KEYWORDS = {
    "QUBT": ["photonic quantum", "photonic qubit", "quantum photonics", "room temperature qubit"],
    "RGTI": ["superconducting qubit", "rigetti", "quantum processor chip"],
    "QBTS": ["quantum annealing", "d-wave", "adiabatic quantum"],
    "IONQ": ["trapped ion", "ion trap", "ionq", "barium qubit"],
    "NVDA": ["gpu computing", "cuda", "large language model training", "AI accelerator"],
    "SMCI": ["ai server", "liquid cooling datacenter", "gpu cluster"],
    "ARQQ": ["quantum encryption", "quantum key distribution", "post-quantum cryptography"],
}


def _clean_text(text: str) -> str:
    """Remove LaTeX math and excessive whitespace from arXiv abstracts."""
    text = re.sub(r"\$[^$]+\$", "[math]", text)
    text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _paper_to_dict(paper: arxiv.Result) -> dict[str, Any]:
    return {
        "arxiv_id": paper.entry_id.split("/")[-1],
        "title": paper.title,
        "authors": [a.name for a in paper.authors[:5]],
        "published": paper.published.strftime("%Y-%m-%d") if paper.published else "",
        "updated": paper.updated.strftime("%Y-%m-%d") if paper.updated else "",
        "abstract": _clean_text(paper.summary)[:800],
        "categories": paper.categories,
        "pdf_url": paper.pdf_url,
        "doi": paper.doi,
    }


@mcp.tool()
def search_papers(
    query: str,
    max_results: int = 5,
    days_back: int = 90,
) -> list[dict[str, Any]]:
    """
    Search arXiv for recent academic papers matching a query.
    Useful for the Tech Agent to understand a company's scientific progress
    and competitive positioning.

    Args:
        query: Search terms (e.g. 'photonic quantum computing error correction')
        max_results: Number of papers to return (default 5, max 20)
        days_back: Only return papers published within this many days (default 90)
    """
    max_results = min(max_results, 20)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    search = arxiv.Search(
        query=query,
        max_results=max_results * 2,  # fetch extra to filter by date
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for paper in arxiv.Client().results(search):
        if paper.published and paper.published.replace(tzinfo=timezone.utc) < cutoff:
            continue
        results.append(_paper_to_dict(paper))
        if len(results) >= max_results:
            break

    return results


@mcp.tool()
def get_papers_for_ticker(
    ticker: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Get the most relevant recent arXiv papers for a specific tracked stock.
    Uses pre-mapped keyword queries tailored to each company's technology.
    This is the primary tool the Tech Agent calls during memo generation.

    Args:
        ticker: Stock ticker symbol (e.g. 'QUBT', 'IONQ', 'RGTI')
        max_results: Number of papers to return per query (default 5)
    """
    ticker = ticker.upper()
    keywords = COMPANY_KEYWORDS.get(ticker, [ticker.lower(), "quantum computing"])

    all_papers: list[dict] = []
    seen_ids: set[str] = set()

    for kw in keywords[:2]:  # Use top 2 keyword sets to limit API calls
        papers = search_papers(kw, max_results=max_results, days_back=180)
        for p in papers:
            if p["arxiv_id"] not in seen_ids:
                seen_ids.add(p["arxiv_id"])
                all_papers.append(p)

    # Sort by date descending
    all_papers.sort(key=lambda x: x["published"], reverse=True)

    return {
        "ticker": ticker,
        "keywords_used": keywords[:2],
        "total_papers": len(all_papers),
        "papers": all_papers[:max_results],
    }


@mcp.tool()
def get_paper_detail(arxiv_id: str) -> dict[str, Any]:
    """
    Fetch full details for a specific arXiv paper by ID.
    Use when the Tech Agent needs to go deeper on a specific paper
    found via search_papers.

    Args:
        arxiv_id: arXiv paper ID (e.g. '2401.12345' or full URL)
    """
    # Normalise ID — strip URL prefix if present
    arxiv_id = arxiv_id.split("/")[-1].replace("abs/", "")

    search = arxiv.Search(id_list=[arxiv_id])
    results = list(arxiv.Client().results(search))

    if not results:
        return {"error": f"Paper not found: {arxiv_id}"}

    paper = results[0]
    data = _paper_to_dict(paper)
    # For detail view, return full abstract (no truncation)
    data["abstract"] = _clean_text(paper.summary)
    return data


@mcp.tool()
def get_sector_research_pulse(sector: str = "quantum computing") -> dict[str, Any]:
    """
    Get a pulse of the latest research activity in a sector.
    Returns recent paper count, top authors, and most active sub-topics.
    Used by the Tech Tracker tab to show research momentum.

    Args:
        sector: Research area (e.g. 'quantum computing', 'photonic computing', 'quantum error correction')
    """
    papers = search_papers(sector, max_results=20, days_back=30)

    if not papers:
        return {"sector": sector, "papers_last_30d": 0, "top_topics": [], "papers": []}

    # Extract sub-topics from titles using simple keyword frequency
    all_words = []
    for p in papers:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", p["title"].lower())
        all_words.extend(words)

    stopwords = {"with", "from", "using", "based", "toward", "through", "this", "that", "their", "quantum"}
    word_freq: dict[str, int] = {}
    for w in all_words:
        if w not in stopwords:
            word_freq[w] = word_freq.get(w, 0) + 1

    top_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:8]

    # Count unique authors
    all_authors = [a for p in papers for a in p["authors"]]
    author_freq: dict[str, int] = {}
    for a in all_authors:
        author_freq[a] = author_freq.get(a, 0) + 1
    top_authors = sorted(author_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "sector": sector,
        "papers_last_30d": len(papers),
        "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
        "top_authors": [{"author": a, "papers": c} for a, c in top_authors],
        "recent_papers": papers[:5],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
