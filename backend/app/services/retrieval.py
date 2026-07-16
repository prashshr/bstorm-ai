import asyncio
import logging
import json
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote

import httpx

from trafilatura import fetch_url, extract

from app.core.config import settings
from app.services.domain_knowledge import enrich_query_with_domains


logger = logging.getLogger("ai_ensemble.rag")

SEARXNG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Ensemble/1.0; +https://ai-ensemble.samkhya.cloud)",
    "Accept": "application/json",
}


def _extract_ddg_url(redirect_url: str) -> str:
    if "uddg=" in redirect_url:
        parsed = urlparse(redirect_url)
        encoded = parse_qs(parsed.query).get("uddg", [None])[0]
        if encoded:
            return unquote(encoded)
    return redirect_url


async def _search_tavily(query: str) -> List[Dict]:
    api_key = settings.tavily_api_key
    if not api_key:
        logger.warning("[RAG] Tavily API key not configured, skipping")
        return []

    logger.info(f"[RAG] Tavily search for: {query[:80]}...")
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": False,
                    "max_results": 10,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                logger.info(f"[RAG] Tavily returned {len(results)} results")
                return [
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "content": r.get("content", ""),
                    }
                    for r in results
                    if r.get("url")
                ]
            else:
                logger.warning(f"[RAG] Tavily returned {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"[RAG] Tavily request failed: {e}")
            return []


async def _search_searxng(query: str) -> List[Dict]:
    base_url = settings.searxng_url
    unique_urls = set()
    results = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{base_url}/search",
                params={"q": query, "format": "json", "language": "en", "categories": "general"},
                headers=SEARXNG_HEADERS,
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("results", []):
                    url = r.get("url")
                    if url and url not in unique_urls:
                        unique_urls.add(url)
                        results.append({
                            "url": url,
                            "title": r.get("title"),
                            "content": r.get("content"),
                        })
                logger.info(f"[RAG] SearXNG returned {len(results)} results from {base_url}")
            else:
                logger.warning(f"[RAG] SearXNG returned {resp.status_code} from {base_url}")
        except Exception as e:
            logger.warning(f"[RAG] SearXNG request to {base_url} failed: {e}")

    return results


async def _search_duckduckgo(query: str) -> List[Dict]:
    unique_urls = set()
    results = []
    logger.info("[RAG] DuckDuckGo fallback search")

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    for attempt in range(2):
        agent = user_agents[attempt % len(user_agents)]
        headers = {
            "User-Agent": agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            if resp.status_code == 200:
                from lxml import html as lh
                tree = lh.fromstring(resp.text)
                for result in tree.xpath("//div[contains(@class, 'result__body')]"):
                    link_el = result.xpath(".//a[contains(@class, 'result__a')]")
                    snippet_el = result.xpath(".//a[contains(@class, 'result__snippet')]")
                    if link_el:
                        real_url = _extract_ddg_url(link_el[0].get("href", ""))
                        title = link_el[0].text_content().strip()
                        snippet = snippet_el[0].text_content().strip() if snippet_el else ""
                        if real_url and real_url not in unique_urls:
                            unique_urls.add(real_url)
                            results.append({"url": real_url, "title": title, "content": snippet})
                logger.info(f"[RAG] DuckDuckGo returned {len(results)} results (attempt {attempt+1})")
                return results
            elif attempt == 0:
                logger.warning(f"[RAG] DuckDuckGo returned {resp.status_code}, retrying with different UA")
                await asyncio.sleep(1)
            else:
                logger.warning(f"[RAG] DuckDuckGo returned {resp.status_code} after retry")
        except Exception as e:
            if attempt == 0:
                logger.warning(f"[RAG] DuckDuckGo failed (attempt {attempt+1}): {e}, retrying...")
                await asyncio.sleep(1)
            else:
                logger.warning(f"[RAG] DuckDuckGo failed (attempt {attempt+1}): {e}")

    return results


async def search_web(queries: List[str]) -> List[Dict]:
    all_results = []
    unique_urls = set()

    for query in queries:
        enriched = enrich_query_with_domains(query)

        engines = {
            "Tavily": _search_tavily(enriched),
            "SearXNG": _search_searxng(enriched),
            "DuckDuckGo": _search_duckduckgo(enriched),
        }

        results_by_engine = await asyncio.gather(*engines.values(), return_exceptions=True)

        for (name, _), results in zip(engines.items(), results_by_engine):
            if isinstance(results, Exception):
                logger.error(f"[RAG] Engine '{name}' failed: {results}")
                continue
            if not results:
                logger.info(f"[RAG] Engine '{name}' returned 0 results")
                continue

            count = 0
            for r in results:
                url = r.get("url", "")
                if url and url not in unique_urls:
                    unique_urls.add(url)
                    r["_source"] = name
                    all_results.append(r)
                    count += 1
            logger.info(f"[RAG] Engine '{name}' contributed {count}/{len(results)} unique results")

        if len(all_results) >= 15:
            break

    total = len(all_results)
    summary = ", ".join(
        f"{e}: {sum(1 for r in all_results if r.get('_source') == e)}"
        for e in ["Tavily", "SearXNG", "DuckDuckGo"]
    )
    logger.info(f"[RAG] Combined {total} results from engines: {summary}")
    return all_results[:15]


async def extract_content_from_urls(urls: List[str]) -> str:
    all_text = []

    for url in urls:
        logger.info(f"[RAG] Fetching content from: {url}")
        try:
            doc = await asyncio.to_thread(fetch_url, url)
            if doc:
                text = await asyncio.to_thread(
                    extract, doc, include_comments=False, include_tables=False
                )
                if text:
                    logger.info(f"[RAG] Extracted {len(text)} chars from {url}")
                    all_text.append(text)
                else:
                    logger.warning(f"[RAG] No text extracted from {url}")
            else:
                logger.warning(f"[RAG] Failed to fetch {url}")
        except Exception as e:
            logger.error(f"[RAG] Error processing {url}: {e}")

    if not all_text:
        logger.warning("[RAG] No content extracted from any URL")
        return ""

    return "\n\n---\n\n".join(all_text)


async def get_retrieved_context(user_prompt: str) -> Optional[str]:
    logger.info(f"[RAG] === Starting RAG pipeline ===")
    try:
        search_results = await asyncio.wait_for(search_web([user_prompt]), timeout=30.0)
        logger.info(f"[RAG] Total search results: {len(search_results)}")

        if not search_results:
            logger.warning("[RAG] No search results found, aborting")
            return None

        # Pull candidate URLs from across all search engines (not just the
        # first engine) so we diversify sources. Some hosts (e.g. Medium) are
        # not fetchable from this environment; mixing in SearXNG/DDG results
        # (Wikipedia, news, vendor blogs) avoids an all-fail extraction pass.
        # De-prioritise known-unfetchable hosts and keep the rest in ranking
        # order, capped at 10 candidates.
        blocked_hosts = {"medium.com"}
        candidates = [r for r in search_results if r.get("url")]
        candidates.sort(
            key=lambda r: (r.get("_source") == "Tavily", r.get("url", "").split("/")[2] in blocked_hosts)
        )
        urls = [r["url"] for r in candidates[:10]]
        logger.info(f"[RAG] Extracting content from {len(urls)} URLs")

        extracted_content = await asyncio.wait_for(extract_content_from_urls(urls), timeout=30.0)
        if not extracted_content:
            logger.warning("[RAG] No content extracted from any URL")
            return None

        sources_lines = []
        for r in search_results:
            engine = r.get("_source", "web")
            title = r.get("title", "")
            url = r.get("url", "")
            sources_lines.append(f"- [{engine}] {title}: {url}")
        sources = "\n".join(sources_lines)
        context = (
            "LIVE WEB RESEARCH CONTEXT — This information was retrieved from the internet "
            "just now via web search. Treat this as factual, up-to-date data for answering "
            "the user's question. You must use this as your primary source for current events, "
            "prices, and time-sensitive information. You may supplement with your own training "
            "data and your own web search or browsing capabilities if you have them.\n\n"
            f"Sources:\n{sources}\n\n"
            f"Content:\n{extracted_content}"
        )
        logger.info(f"[RAG] === RAG SUCCESS === Context size: {len(context)} chars")
        return context

    except asyncio.TimeoutError:
        logger.warning("[RAG] === RAG TIMEOUT === Pipeline exceeded 60s limit")
        return None
    except Exception as e:
        logger.error(f"[RAG] === RAG FAILED === {e}", exc_info=True)
        return None
