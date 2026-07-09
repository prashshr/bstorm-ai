import pytest
from app.services.domain_knowledge import (
    classify_query,
    enrich_query_with_domains,
    TOPIC_DATABASE,
)


class TestDomainKnowledge:
    def test_topic_categories_count(self):
        assert len(TOPIC_DATABASE) >= 17, "Should have 17+ topic categories"

    def test_all_topics_have_domains(self):
        for topic in TOPIC_DATABASE:
            assert len(topic.domains) > 0, f"Topic '{topic.name}' has no domains"
            assert len(topic.keywords) > 0, f"Topic '{topic.name}' has no keywords"

    def test_classify_shopping(self):
        topic, score, obj = classify_query("best smartphone under 300 euros Berlin")
        assert topic == "shopping"
        assert score >= 3

    def test_classify_finance(self):
        topic, score, obj = classify_query("nvidia stock performance 2026 dividend yield")
        assert topic == "finance"
        assert score >= 3

    def test_classify_technology(self):
        topic, score, obj = classify_query("how to deploy kubernetes cluster docker")
        assert topic == "technology"
        assert score >= 3

    def test_classify_health(self):
        topic, score, obj = classify_query("symptoms of diabetes treatment medication")
        assert topic == "health"
        assert score >= 3

    def test_classify_news(self):
        topic, score, obj = classify_query("breaking news today election results")
        assert topic == "news"
        assert score >= 3

    def test_classify_science(self):
        topic, score, obj = classify_query("quantum computing research paper 2026")
        assert topic == "science"
        assert score >= 3

    def test_classify_sports(self):
        topic, score, obj = classify_query("bundesliga match result bayern munich")
        assert topic == "sports"
        assert score >= 3

    def test_classify_food(self):
        topic, score, obj = classify_query("easy vegan recipe dinner healthy")
        assert topic == "food"
        assert score >= 3

    def test_classify_local(self):
        topic, score, obj = classify_query("best restaurant in berlin mitte near me")
        assert topic == "local"
        assert score >= 3

    def test_classify_career(self):
        topic, score, obj = classify_query("software engineer job interview salary negotiation")
        assert topic == "career"
        assert score >= 3

    def test_classify_automotive(self):
        topic, score, obj = classify_query("tesla model 3 review electric car range battery")
        assert topic == "automotive"
        assert score >= 3

    def test_classify_real_estate(self):
        topic, score, obj = classify_query("apartment for rent berlin 2 bedroom wg")
        assert topic == "real_estate"
        assert score >= 3

    def test_classify_education(self):
        topic, score, obj = classify_query("best online course learn python programming")
        assert topic == "education"
        assert score >= 3

    def test_classify_legal(self):
        topic, score, obj = classify_query("tenant rights eviction notice lease contract")
        assert topic == "legal"
        assert score >= 3

    def test_classify_entertainment(self):
        topic, score, obj = classify_query("best movie 2026 review imdb rating")
        assert topic == "entertainment"
        assert score >= 3

    def test_classify_fashion(self):
        topic, score, obj = classify_query("best sneakers 2026 nike adidas新款")
        assert topic == "fashion"
        assert score >= 3

    def test_classify_photography(self):
        topic, score, obj = classify_query("best mirrorless camera sony canon nikon lens")
        assert topic == "photography"
        assert score >= 3

    def test_generic_query_returns_low_confidence(self):
        topic, score, obj = classify_query("hello world how are you")
        assert score < 3

    def test_enrich_shopping_query(self):
        enriched = enrich_query_with_domains("best smartphone under 300 euros")
        assert "site:" in enriched
        assert "idealo.de" in enriched
        assert "geizhals.de" in enriched

    def test_enrich_finance_query(self):
        enriched = enrich_query_with_domains("nvidia stock dividend yield 2026")
        assert "site:" in enriched

    def test_enrich_tech_query(self):
        enriched = enrich_query_with_domains("kubernetes docker deployment microservice api")
        assert "site:" in enriched

    def test_enrich_generic_query_no_domains(self):
        enriched = enrich_query_with_domains("hello world")
        assert "site:" not in enriched

    def test_enrich_health_query(self):
        enriched = enrich_query_with_domains("symptoms of diabetes treatment")
        assert "site:" in enriched
        assert "mayoclinic.org" in enriched or "who.int" in enriched

    def test_enrich_local_query(self):
        enriched = enrich_query_with_domains("restaurant in berlin mitte")
        assert "site:" in enriched

    def test_sub_keyword_boosts_score(self):
        topic, score_no, _ = classify_query("car")
        topic, score_yes, _ = classify_query("best electric car range battery charging tesla model 3")
        assert score_yes > score_no

    def test_all_20_topics_have_sub_keywords(self):
        for topic in TOPIC_DATABASE:
            assert len(topic.sub_keywords) >= 2, f"Topic '{topic.name}' has fewer than 2 sub-categories"

    def test_no_topic_dominated_by_single_query(self):
        topic, score, _ = classify_query("the and of to in for is on at by with from")
        assert score < 3
