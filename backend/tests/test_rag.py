import pytest
from unittest.mock import patch, AsyncMock
from app.services.retrieval import (
    get_retrieved_context,
    _extract_ddg_url,
    search_web,
    extract_content_from_urls,
)


class TestRagPipeline:
    @pytest.mark.asyncio
    async def test_extract_ddg_url_decodes_properly(self):
        url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
        result = _extract_ddg_url(url)
        assert result == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_extract_ddg_url_regular_url_passthrough(self):
        url = "https://example.com/page"
        result = _extract_ddg_url(url)
        assert result == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_extract_ddg_url_empty_returns_empty(self):
        result = _extract_ddg_url("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_search_web_no_engines_returns_empty(self):
        with patch("app.services.retrieval._search_tavily", return_value=[]), \
             patch("app.services.retrieval._search_searxng", return_value=[]), \
             patch("app.services.retrieval._search_duckduckgo", return_value=[]):
            results = await search_web(["test query"])
            assert results == []

    @pytest.mark.asyncio
    async def test_search_web_deduplicates_urls(self):
        with patch("app.services.retrieval._search_tavily", return_value=[
            {"url": "https://a.com", "title": "A", "content": "AAA"},
            {"url": "https://b.com", "title": "B", "content": "BBB"},
        ]), patch("app.services.retrieval._search_searxng", return_value=[
            {"url": "https://a.com", "title": "A dup", "content": "AAA dup"},
            {"url": "https://c.com", "title": "C", "content": "CCC"},
        ]), patch("app.services.retrieval._search_duckduckgo", return_value=[]):
            results = await search_web(["test"])
            assert len(results) == 3
            urls = [r["url"] for r in results]
            assert urls == ["https://a.com", "https://b.com", "https://c.com"]

    @pytest.mark.asyncio
    async def test_search_web_one_engine_fails_others_still_work(self):
        with patch("app.services.retrieval._search_tavily", side_effect=Exception("API down")), \
             patch("app.services.retrieval._search_searxng", return_value=[
                 {"url": "https://x.com", "title": "X", "content": "XXX"},
             ]), patch("app.services.retrieval._search_duckduckgo", return_value=[]):
            results = await search_web(["test"])
            assert len(results) == 1
            assert results[0]["url"] == "https://x.com"

    @pytest.mark.asyncio
    async def test_search_web_respects_max_15_results(self):
        many_results = [
            {"url": f"https://{i}.com", "title": str(i), "content": str(i)}
            for i in range(20)
        ]
        with patch("app.services.retrieval._search_tavily", return_value=many_results), \
             patch("app.services.retrieval._search_searxng", return_value=[]), \
             patch("app.services.retrieval._search_duckduckgo", return_value=[]):
            results = await search_web(["test"])
            assert len(results) <= 15

    @pytest.mark.asyncio
    async def test_extract_content_empty_urls(self):
        result = await extract_content_from_urls([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_get_retrieved_context_no_search_results(self):
        with patch("app.services.retrieval.search_web", return_value=[]):
            result = await get_retrieved_context("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_retrieved_context_returns_formatted_string(self):
        with patch("app.services.retrieval.search_web", return_value=[
            {"url": "https://example.com", "title": "Example", "content": "Test", "_source": "Tavily"},
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value="Extracted content"):
            result = await get_retrieved_context("test query")
            assert result is not None
            assert "LIVE WEB RESEARCH CONTEXT" in result
            assert "[Tavily]" in result
            assert "Extracted content" in result
            assert "RAG data:" in result

    @pytest.mark.asyncio
    async def test_get_retrieved_context_engine_attribution_in_sources(self):
        with patch("app.services.retrieval.search_web", return_value=[
            {"url": "https://a.com", "title": "A", "content": "A", "_source": "Tavily"},
            {"url": "https://b.com", "title": "B", "content": "B", "_source": "SearXNG"},
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value="content"):
            result = await get_retrieved_context("test")
            assert "[Tavily]" in result
            assert "[SearXNG]" in result
