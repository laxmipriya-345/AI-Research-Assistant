"""
Web Search Tool
-----------------
Thin wrapper around the `ddgs` (DuckDuckGo Search) package so the agent
can look up current information. No API key required.
"""
from config import WEB_SEARCH_MAX_RESULTS


def web_search(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> list:
    """
    Returns a list of {title, url, snippet} dicts.
    Falls back gracefully (returns []) if the search backend is unreachable,
    so the agent can inform the user rather than crash.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS  # older package name fallback

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]

    return results
