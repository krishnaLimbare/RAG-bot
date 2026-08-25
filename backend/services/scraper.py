"""Web scraping service for study research."""

import asyncio
import logging
import re
from typing import Optional

from backend.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


def clean_markdown(text: str) -> str:
    """Remove image markdown links and excessive whitespace."""
    text = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[\\s*\]\([^)]+\.(png|jpg|jpeg|gif|bmp|svg)\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class WebScraper:
    """Scrapes web content for study research and optionally embeds it."""

    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def scrape_url(self, url: str, css_selector: Optional[str] = None) -> dict:
        """Scrape a single URL and return cleaned content."""
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler(browser_type="chromium", headless=True) as crawler:
                kwargs = {
                    "url": url,
                    "exclude_external_links": True,
                    "exclude_social_media_links": True,
                    "exclude_external_images": True,
                }
                if css_selector:
                    kwargs["css_selector"] = css_selector

                result = await crawler.arun(**kwargs)

                if result.success:
                    cleaned = clean_markdown(result.markdown)
                    return {
                        "success": True,
                        "url": url,
                        "content": cleaned,
                        "title": getattr(result, "title", url),
                    }
                else:
                    return {
                        "success": False,
                        "url": url,
                        "error": getattr(result, "error_message", "Unknown error"),
                    }
        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
            return {"success": False, "url": url, "error": str(e)}

    async def search_and_scrape(self, topic: str, max_results: int = 3) -> dict:
        """Search for a topic using DuckDuckGo and scrape top results."""
        try:
            import httpx

            # Use DuckDuckGo HTML search (no API key needed)
            search_url = "https://html.duckduckgo.com/html/"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(search_url, data={"q": topic})
                html = resp.text

            # Extract URLs from DuckDuckGo results
            url_pattern = r'href="(https?://[^"]+)"'
            found_urls = re.findall(url_pattern, html)
            # Filter out DuckDuckGo internal links and tracking URLs
            clean_urls = []
            for u in found_urls:
                if "duckduckgo.com" in u:
                    continue
                if u.startswith("https://links.duckduckgo.com"):
                    # Extract the actual URL from the redirect
                    actual = re.search(r"uddg=([^&]+)", u)
                    if actual:
                        from urllib.parse import unquote
                        clean_urls.append(unquote(actual.group(1)))
                else:
                    clean_urls.append(u)

            urls = clean_urls[:max_results]
            if not urls:
                return {"success": False, "error": "No search results found", "results": []}

            # Scrape each URL
            results = []
            for url in urls:
                result = await self.scrape_url(url)
                if result["success"]:
                    # Truncate very long content for the response
                    content = result["content"]
                    results.append({
                        "url": url,
                        "title": result.get("title", url),
                        "content": content[:5000] if len(content) > 5000 else content,
                        "full_length": len(content),
                    })

            return {"success": True, "topic": topic, "results": results}

        except Exception as e:
            logger.error(f"Search error for topic '{topic}': {e}")
            return {"success": False, "error": str(e), "results": []}

    def add_to_knowledge_base(self, content: str, source_name: str) -> dict:
        """Embed scraped content into the vector store."""
        return self.embedding_service.process_text(content, source_name)
