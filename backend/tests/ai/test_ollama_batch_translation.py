"""Ollama's batched-translation wire contract.

The behaviour pinned here came from a real local-model response: asked for four
translations it produced three valid entries and one with `"id": ": 1"`. The
first implementation validated the whole response at once, so that single bad
id discarded three good translations and sent all four items back individually.
Entries are therefore validated one at a time.

No test here contacts Ollama; `_post` is stubbed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.ai.errors import AIProviderError
from app.ai.ollama_provider import OllamaAIProvider
from app.ai.schemas import BatchTranslationItem, BatchTranslationRequest


def _provider(responses: list[str]) -> tuple[OllamaAIProvider, list[str]]:
    provider = OllamaAIProvider("http://ollama.invalid", "test-model")
    prompts: list[str] = []
    remaining = list(responses)

    async def fake_post(payload: dict[str, Any]) -> str:
        prompts.append(payload["prompt"])
        return remaining.pop(0) if remaining else ""

    provider._post = fake_post  # type: ignore[method-assign]
    return provider, prompts


def _request(*texts: str) -> BatchTranslationRequest:
    return BatchTranslationRequest(
        items=[BatchTranslationItem(id=index, text=t) for index, t in enumerate(texts)],
        sourceLanguage="en",
        targetLanguage="de",
    )


@pytest.mark.asyncio
async def test_one_malformed_id_does_not_discard_the_valid_entries() -> None:
    """The exact observed response shape."""
    response = json.dumps(
        {
            "translations": [
                {"id": 0, "translatedText": "Küche"},
                {"id": ": 1", "translatedText": "Badezimmer"},
                {"id": 2, "translatedText": "der Kellerraum"},
                {"id": 3, "translatedText": "die Waschküche"},
            ]
        }
    )
    provider, _ = _provider([response])

    result = await provider.translate_output_batch(
        _request("Küche,", "Badezimmer mit WC,", "der Kellerraum,", "die Waschküche")
    )

    assert result.translations_by_id == {
        0: "Küche",
        2: "der Kellerraum",
        3: "die Waschküche",
    }
    assert 1 not in result.translations_by_id, "the malformed entry must be dropped"


@pytest.mark.asyncio
async def test_unrequested_id_is_ignored() -> None:
    response = json.dumps(
        {
            "translations": [
                {"id": 0, "translatedText": "Vorname"},
                {"id": 99, "translatedText": "Erfunden"},
            ]
        }
    )
    provider, _ = _provider([response])

    result = await provider.translate_output_batch(_request("First name"))

    assert result.translations_by_id == {0: "Vorname"}


@pytest.mark.asyncio
async def test_duplicated_id_keeps_the_first_value() -> None:
    """A repeated id must not let a later entry overwrite an earlier field."""
    response = json.dumps(
        {
            "translations": [
                {"id": 0, "translatedText": "Vorname"},
                {"id": 0, "translatedText": "Nachname"},
            ]
        }
    )
    provider, _ = _provider([response])

    result = await provider.translate_output_batch(_request("First name"))

    assert result.translations_by_id == {0: "Vorname"}


@pytest.mark.asyncio
async def test_entry_with_extra_commentary_key_is_dropped() -> None:
    """A model that decorates an entry with its reasoning is not partially
    trusted — the entry is dropped so the caller falls back for it."""
    response = json.dumps(
        {
            "translations": [
                {"id": 0, "translatedText": "Vorname"},
                {
                    "id": 1,
                    "translatedText": "Nachname",
                    "reasoning": "the user's surname",
                },
            ]
        }
    )
    provider, _ = _provider([response])

    result = await provider.translate_output_batch(_request("First name", "Last name"))

    assert result.translations_by_id == {0: "Vorname"}


@pytest.mark.asyncio
async def test_blank_translation_is_treated_as_missing() -> None:
    response = json.dumps(
        {
            "translations": [
                {"id": 0, "translatedText": "   "},
                {"id": 1, "translatedText": "Nachname"},
            ]
        }
    )
    provider, _ = _provider([response])

    result = await provider.translate_output_batch(_request("First name", "Last name"))

    assert result.translations_by_id == {1: "Nachname"}


@pytest.mark.asyncio
async def test_wrong_envelope_gets_exactly_one_repair_attempt() -> None:
    bad = json.dumps({"result": ["Vorname"]})
    good = json.dumps({"translations": [{"id": 0, "translatedText": "Vorname"}]})
    provider, prompts = _provider([bad, good])

    result = await provider.translate_output_batch(_request("First name"))

    assert result.translations_by_id == {0: "Vorname"}
    assert len(prompts) == 2, "expected one repair attempt, no more"


@pytest.mark.asyncio
async def test_persistently_malformed_envelope_raises_a_safe_error() -> None:
    bad = json.dumps({"result": ["Vorname"]})
    provider, _ = _provider([bad, bad])

    with pytest.raises(AIProviderError) as excinfo:
        await provider.translate_output_batch(_request("First name"))

    # Never leak the raw model output.
    assert "Vorname" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_empty_request_makes_no_call() -> None:
    provider, prompts = _provider([])

    result = await provider.translate_output_batch(
        BatchTranslationRequest(items=[], sourceLanguage="en", targetLanguage="de")
    )

    assert result.translations_by_id == {}
    assert prompts == []


@pytest.mark.asyncio
async def test_prompt_carries_the_items_and_the_untrusted_data_warning() -> None:
    good = json.dumps({"translations": [{"id": 0, "translatedText": "Vorname"}]})
    provider, prompts = _provider([good])

    await provider.translate_output_batch(_request("First name"))

    assert '"text": "First name"' in prompts[0]
    assert "untrusted data" in prompts[0]
