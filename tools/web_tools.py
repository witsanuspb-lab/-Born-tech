import html
import json
import re
import urllib.parse
import urllib.request


def web_search(query: str, max_results: int = 6) -> str:
    """Search via DuckDuckGo Instant Answer API (no key required)."""
    try:
        params = urllib.parse.urlencode({"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"})
        url = f"https://api.duckduckgo.com/?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        parts = []

        if data.get("AbstractText"):
            parts.append(f"**Answer:** {data['AbstractText']}")
            if data.get("AbstractURL"):
                parts.append(f"Source: {data['AbstractURL']}")
            parts.append("")

        topics = data.get("RelatedTopics", [])
        count = 0
        for t in topics:
            if count >= max_results:
                break
            if isinstance(t, dict) and t.get("Text"):
                link = t.get("FirstURL", "")
                parts.append(f"• {t['Text']}")
                if link:
                    parts.append(f"  {link}")
                count += 1
            elif isinstance(t, dict) and t.get("Topics"):
                for sub in t["Topics"]:
                    if count >= max_results:
                        break
                    if sub.get("Text"):
                        parts.append(f"• {sub['Text']}")
                        if sub.get("FirstURL"):
                            parts.append(f"  {sub['FirstURL']}")
                        count += 1

        return "\n".join(parts) if parts else f"No results found for: {query}"
    except Exception as e:
        return f"Search failed: {e}"


def fetch_webpage(url: str, max_chars: int = 8000) -> str:
    """Fetch a URL and return its plain-text content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")

        # Strip script/style blocks
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Strip all tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Decode entities
        text = html.unescape(text)

        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n[Truncated — {len(text):,} chars total]"
        return text
    except Exception as e:
        return f"Failed to fetch {url}: {e}"
