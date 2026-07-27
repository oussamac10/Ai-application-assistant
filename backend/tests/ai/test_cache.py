"""Tests for AIResponseCache."""

from app.ai.cache import AIResponseCache


def test_cache_disabled_by_default() -> None:
    cache = AIResponseCache(enabled=False)
    data = {"field_type": "money", "answer": "1800 EUR"}
    cache.set(data, {"amount": 1800})
    assert cache.get(data) is None
    assert cache.size == 0


def test_cache_stores_and_retrieves() -> None:
    cache = AIResponseCache(enabled=True)
    data = {"field_type": "money", "answer": "1800 EUR"}
    value = {"amount": 1800, "currency": "EUR"}
    cache.set(data, value)
    assert cache.get(data) == value


def test_cache_miss_for_different_input() -> None:
    cache = AIResponseCache(enabled=True)
    cache.set({"key": "a"}, "value_a")
    assert cache.get({"key": "b"}) is None


def test_cache_clear() -> None:
    cache = AIResponseCache(enabled=True)
    cache.set({"key": "a"}, "value_a")
    cache.clear()
    assert cache.size == 0
    assert cache.get({"key": "a"}) is None


def test_cache_same_content_different_order() -> None:
    """Key stability: dict with same keys in different order hits the same entry."""
    cache = AIResponseCache(enabled=True)
    cache.set({"b": 2, "a": 1}, "value")
    result = cache.get({"a": 1, "b": 2})
    assert result == "value"


def test_cache_key_includes_target_language() -> None:
    """Prevents a language-cache bug: a question translated for one target
    language must never be served for a different one — the cache key must
    include target_language (or any field that varies by language) so an
    English-cached entry is never reused for a German request."""
    cache = AIResponseCache(enabled=True)
    request_en = {
        "question_key": "personal.first_name",
        "text": "What is your first name?",
        "source_language": "en",
        "target_language": "en",
    }
    cache.set(request_en, "What is your first name?")

    request_de = {**request_en, "target_language": "de"}
    assert cache.get(request_de) is None

    request_ar = {**request_en, "target_language": "ar"}
    assert cache.get(request_ar) is None

    # The original English entry is still retrievable under its own key.
    assert cache.get(request_en) == "What is your first name?"
