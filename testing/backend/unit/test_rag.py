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
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value=[
            {"url": "https://example.com", "content": "Extracted content"},
        ]):
            result = await get_retrieved_context("test query")
            assert result is not None
            assert "UNTRUSTED WEB DATA" in result
            assert "[Tavily]" in result
            assert "Extracted content" in result

    @pytest.mark.asyncio
    async def test_get_retrieved_context_engine_attribution_in_sources(self):
        with patch("app.services.retrieval.search_web", return_value=[
            {"url": "https://a.com", "title": "A", "content": "A", "_source": "Tavily"},
            {"url": "https://b.com", "title": "B", "content": "B", "_source": "SearXNG"},
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value=[
            {"url": "https://a.com", "content": "content"},
            {"url": "https://b.com", "content": "content"},
        ]):
            result = await get_retrieved_context("test")
            assert "[Tavily]" in result
            assert "[SearXNG]" in result

    @pytest.mark.asyncio
    async def test_get_retrieved_context_falls_back_to_snippets_when_extraction_fails(self):
        from app.services.retrieval import _RAG_CACHE
        _RAG_CACHE.clear()
        with patch("app.services.retrieval.search_web", return_value=[
            {"url": "https://example.com", "title": "Example", "content": "Rich snippet from Tavily about fallback query", "_source": "Tavily"},
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value=""):
            result = await get_retrieved_context("fallback query")
            assert result is not None
            assert "Rich snippet from Tavily" in result
            assert "### [Tavily] Example" in result

    @pytest.mark.asyncio
    async def test_get_retrieved_context_filters_unrelated_cookie_snippets(self):
        from app.services.retrieval import _RAG_CACHE
        _RAG_CACHE.clear()
        with patch("app.services.retrieval.search_web", return_value=[
            {
                "url": "https://example.com/altcoins",
                "title": "Altcoin market outlook",
                "content": "Altcoin market breadth and liquidity are improving.",
                "_source": "Tavily",
            },
            {
                "url": "https://example.com/cookies",
                "title": "Yahoo Finance",
                "content": "Cookie consent. Accept all cookies. Privacy choices and tracking technologies.",
                "_source": "SearXNG",
            },
        ]), patch("app.services.retrieval.extract_content_from_urls", return_value=[]):
            result = await get_retrieved_context("Analyze the altcoin market")

        assert result is not None
        assert "Altcoin market outlook" in result
        assert "Cookie consent" not in result

    @pytest.mark.asyncio
    async def test_get_retrieved_context_blends_topic_context_for_followup(self):
        with patch("app.services.retrieval.search_web", AsyncMock(return_value=[
            {"url": "https://example.com", "title": "Example", "content": "AI companies and AI stocks", "_source": "Tavily"},
        ])) as mock_search, patch("app.services.retrieval.extract_content_from_urls", return_value=[
            {"url": "https://example.com", "content": "Extracted"},
        ]):
            result = await get_retrieved_context(
                user_prompt="recommend next 5",
                topic_context="AI companies under 50B",
            )
            assert result is not None
            assert mock_search.called
            called_queries = mock_search.call_args[0][0]
            assert any("recommend next 5 AI companies under 50B" in q for q in called_queries)

    def test_candidate_rank_prioritizes_unblocked_and_tavily(self):
        from app.services.retrieval import _candidate_rank
        tavily_unblocked = {"url": "https://reuters.com/article", "_source": "Tavily"}
        searxng_unblocked = {"url": "https://bloomberg.com/news", "_source": "SearXNG"}
        blocked = {"url": "https://amazon.com/dp/123", "_source": "Tavily"}
        odd_url = {"url": "not-a-valid-url", "_source": "DuckDuckGo"}

        rank_tavily = _candidate_rank(tavily_unblocked)
        rank_searxng = _candidate_rank(searxng_unblocked)
        rank_blocked = _candidate_rank(blocked)
        rank_odd = _candidate_rank(odd_url)

        # Unblocked must rank before blocked
        assert rank_tavily < rank_blocked
        # Tavily unblocked must rank before SearXNG unblocked
        assert rank_tavily < rank_searxng
        # Odd URL must not raise exception
        assert rank_odd is not None

    def test_extract_search_queries_crypto_and_indicators(self):
        from app.services.retrieval import extract_search_queries
        prompt = (
            "Act as an independent crypto technical analyst. Audit these supplied pure-model targets: "
            "ETH 1936, SOL 78.62, NEAR 1.29, HYPE 48.50, AAVE 88.20. Limit low enough for a BTC 200D retest. "
            "Return one concise table. Cite data sources and timestamp."
        )
        queries = extract_search_queries(prompt)
        assert len(queries) >= 2
        # Must have extracted crypto price query with detected tickers
        assert any("crypto prices" in q and "ETH" in q and "SOL" in q for q in queries)
        # Must have extracted 200D moving average indicator query
        assert any("200 day moving average" in q or "200D SMA" in q for q in queries)
        # Must not contain instruction boilerplate
        assert not any("Act as an independent" in q for q in queries)

    def test_extract_search_queries_short_prompt(self):
        from app.services.retrieval import extract_search_queries
        queries = extract_search_queries("latest AI breakthroughs in quantum computing")
        assert "latest AI breakthroughs in quantum computing" in queries
