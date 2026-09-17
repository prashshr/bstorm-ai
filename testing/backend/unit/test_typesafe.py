import pytest
from unittest.mock import patch, MagicMock
from app.services.typesafe_service import should_search_web, evaluate_system_one

class TestTypeSafeService:
    @pytest.mark.asyncio
    async def test_should_search_web_without_api_key_falls_back_to_true(self):
        with patch("app.services.typesafe_service.get_typesafe_api_key", return_value=""):
            # Without API key, safe fallback returns True so search is not skipped
            assert await should_search_web("What is 2 + 2?") is True

    @pytest.mark.asyncio
    async def test_should_search_web_with_system_one_noul(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "answers": {
                "needs_web_search": {
                    "noul": 0.15,
                    "confidence": 0.95
                }
            }
        }

        with patch("app.services.typesafe_service.get_typesafe_api_key", return_value="mock_key"):
            with patch("httpx.AsyncClient.post", return_value=mock_response):
                # Probability 0.15 is < 0.65, so should_search_web returns False (saving tokens/latency!)
                decision = await should_search_web("What is 2 + 2?")
                assert decision is False

        mock_response.json.return_value = {
            "answers": {
                "needs_web_search": {
                    "noul": 0.88,
                    "confidence": 0.98
                }
            }
        }
        with patch("app.services.typesafe_service.get_typesafe_api_key", return_value="mock_key"):
            with patch("httpx.AsyncClient.post", return_value=mock_response):
                # Probability 0.88 is >= 0.65, so should_search_web returns True
                decision = await should_search_web("Who won the 2026 World Cup?")
                assert decision is True

    @pytest.mark.asyncio
    async def test_evaluate_system_one_handles_api_error_gracefully(self):
        with patch("app.services.typesafe_service.get_typesafe_api_key", return_value="mock_key"):
            with patch("httpx.AsyncClient.post", side_effect=Exception("API connection timeout")):
                res = await evaluate_system_one("test prompt", {"type": "object"})
                assert res is None
