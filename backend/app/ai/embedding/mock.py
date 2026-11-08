"""Deterministic mock embedding provider for tests and local development.

Produces stable 128-dimensional unit vectors based on token and n-gram hashing
with semantic clustering so synonymous administrative terms achieve realistic
cosine similarity without external API calls or latency.
"""

from __future__ import annotations

import hashlib
import re
from typing import ClassVar

from app.ai.embedding.similarity import normalize_vector


class MockEmbeddingProvider:
    """Deterministic, zero-cost embedding provider for unit tests and local dev."""

    DIMENSIONS: int = 128

    # Semantic keyword clusters for administrative form concepts
    _SEMANTIC_ANCHORS: ClassVar[dict[str, list[str]]] = {
        "first_name": [
            "vorname",
            "first name",
            "given name",
            "prenom",
            "first_name",
            "applicant_first_name",
        ],
        "last_name": [
            "nachname",
            "familienname",
            "last name",
            "surname",
            "family name",
            "nom",
            "last_name",
        ],
        "birth_date": [
            "geburtsdatum",
            "date of birth",
            "birth date",
            "dob",
            "date de naissance",
            "geburtstag",
        ],
        "birth_place": [
            "geburtsort",
            "place of birth",
            "birth place",
            "lieu de naissance",
        ],
        "nationality": [
            "staatsangehoerigkeit",
            "nationality",
            "citizenship",
            "nationalite",
        ],
        "email": ["email", "e-mail", "email address", "e-mail-adresse", "courriel"],
        "phone": [
            "telefon",
            "phone",
            "telephone",
            "phone number",
            "telefonnummer",
            "mobil",
        ],
        "address": [
            "anschrift",
            "address",
            "wohnort",
            "adresse",
            "street",
            "strasse",
            "plz",
            "postal code",
        ],
        "iban": ["iban", "bankverbindung", "kontonummer", "bank account", "bic"],
        "move_in_date": ["einzugsdatum", "move in date", "move-in", "einzug"],
        "signature": [
            "unterschrift",
            "signature",
            "unterschrift der antragstellenden person",
            "sign",
        ],
    }

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    def _embed_text(self, text: str) -> list[float]:
        vec = [0.0] * self.DIMENSIONS
        normalized = text.strip().lower()
        if not normalized:
            return vec

        # 1. Check anchor cluster overlap for strong semantic alignment
        for anchor_idx, (_anchor_name, variants) in enumerate(
            self._SEMANTIC_ANCHORS.items()
        ):
            for v in variants:
                if v in normalized or normalized in v:
                    # Boost specific dimensions allocated to this cluster
                    cluster_offset = (anchor_idx * 7) % self.DIMENSIONS
                    for j in range(5):
                        dim = (cluster_offset + j) % self.DIMENSIONS
                        vec[dim] += 2.5

        # 2. Token and 3-gram feature hashing for general vocabulary
        words = re.findall(r"\w+", normalized)
        for w in words:
            # Hash word to dimension
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16)
            dim = h % self.DIMENSIONS
            vec[dim] += 1.0

            # 3-grams
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    trigram = w[i : i + 3]
                    th = int(hashlib.md5(trigram.encode("utf-8")).hexdigest()[:8], 16)
                    vec[th % self.DIMENSIONS] += 0.3

        return normalize_vector(vec)

    async def get_embedding(self, text: str) -> list[float]:
        return self._embed_text(text)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(t) for t in texts]
