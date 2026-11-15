"""AI Schema Auto-Mapper Service for Review Studio.

Automatically matches detected PDF form fields to canonical Profile Vault keys
using semantic vector embeddings, lexical anchors, and data type compatibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding.factory import get_embedding_provider
from app.ai.embedding.protocol import EmbeddingProvider
from app.ai.embedding.similarity import cosine_similarity
from app.forms.canonical_catalog import (
    CANONICAL_SCHEMA_CATALOG,
    CanonicalFieldDefinition,
)
from app.forms.learning_service import FormPatternLearningService
from app.forms.models import FormField, FormTemplate, FormVersion
from app.forms.services import ResourceNotFoundError

logger = logging.getLogger(__name__)


def get_field_primary_label(field: FormField, source_language: str = "de") -> str:
    """Extracts primary human-readable question label for a form field."""
    for t in field.translations:
        if t.language == source_language and t.label:
            return t.label
    if field.translations and field.translations[0].label:
        return field.translations[0].label
    if field.configuration and field.configuration.get("label"):
        return str(field.configuration["label"])
    return field.key.replace("_", " ")


@dataclass
class AutoMapAlternative:
    key: str
    label: str
    confidence: float


@dataclass
class AutoMapFieldResult:
    field_id: str
    field_key: str
    field_label: str
    current_question_key: str | None
    suggested_question_key: str | None
    confidence: float
    match_reason: str
    alternatives: list[AutoMapAlternative]


class SchemaAutoMapperService:
    """Computes and applies semantic key mappings for form schema fields."""

    def __init__(
        self,
        db: Session,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.db = db
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self._canonical_catalog = CANONICAL_SCHEMA_CATALOG
        self._canonical_embeddings: list[list[float]] | None = None

    async def _ensure_canonical_embeddings(self) -> list[list[float]]:
        if self._canonical_embeddings is None:
            texts = [c.semantic_text for c in self._canonical_catalog]
            self._canonical_embeddings = await self.embedding_provider.get_embeddings(
                texts
            )
        return self._canonical_embeddings

    def _type_compatibility_score(self, field_type: str, canonical_type: str) -> float:
        """Returns 1.0 for perfect match, 0.7 for compatible, 0.2 for mismatch."""
        f_type = (field_type or "string").lower()
        c_type = canonical_type.lower()
        if f_type == c_type:
            return 1.0
        if f_type in ("string", "text", "multiline_text") and c_type in (
            "string",
            "date",
            "number",
        ):
            return 0.8
        if f_type == "signature" or c_type == "signature":
            return 0.1  # Signature is strict
        return 0.5

    def _lexical_anchor_score(
        self, label: str, field_key: str, candidate: CanonicalFieldDefinition
    ) -> float:
        """Calculates fast token/synonym overlap score between field and candidate."""
        tokens = set((label + " " + field_key.replace("_", " ")).lower().split())
        score = 0.0

        for syn in candidate.synonyms_de + candidate.synonyms_en:
            syn_lower = syn.lower()
            if syn_lower in label.lower() or syn_lower in field_key.lower():
                return 1.0  # Exact substring hit
            syn_tokens = set(syn_lower.split())
            if (
                tokens
                and syn_tokens
                and (tokens.issubset(syn_tokens) or syn_tokens.issubset(tokens))
            ):
                score = max(score, 0.85)

        return score

    async def auto_map_fields(
        self,
        organization_id: str,
        template_id: str,
        min_confidence: float = 0.45,
    ) -> list[AutoMapFieldResult]:
        """Analyzes all fields in the latest form version and computes suggested mappings."""
        # 1. Fetch form template and latest version
        stmt = select(FormTemplate).where(
            FormTemplate.id == template_id,
            FormTemplate.organization_id == organization_id,
        )
        template = self.db.scalars(stmt).first()
        if not template:
            raise ResourceNotFoundError(f"Form template '{template_id}' not found.")

        v_stmt = (
            select(FormVersion)
            .where(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
        )
        latest_version = self.db.scalars(v_stmt).first()
        if not latest_version:
            raise ResourceNotFoundError("No form version found for template.")

        fields = latest_version.fields
        if not fields:
            return []

        # 2. Get embeddings for canonical catalog and form fields
        canonical_vecs = await self._ensure_canonical_embeddings()

        # Build prompt strings for form fields
        field_texts = []
        for f in fields:
            label = get_field_primary_label(f, latest_version.source_language)
            field_texts.append(f"{label} (key: {f.key}, type: {f.field_type})")

        field_vecs = await self.embedding_provider.get_embeddings(field_texts)
        learning_service = FormPatternLearningService(self.db)
        learned_candidates = learning_service.load_candidates(
            organization_id=organization_id,
            source_language=latest_version.source_language or "de",
        )

        results: list[AutoMapFieldResult] = []

        # 3. Score each field against learned patterns + canonical catalog
        for f_idx, field in enumerate(fields):
            f_vec = field_vecs[f_idx]
            field_label = get_field_primary_label(field, latest_version.source_language)

            # Secondary table rows (e.g., spouse / child rows 2..N) must never
            # auto-bind to the main applicant's personal Vault keys.
            tbl_meta = (
                (field.configuration or {}).get("table")
                if isinstance(field.configuration, dict)
                else None
            )
            if isinstance(tbl_meta, dict) and int(tbl_meta.get("row_index") or 1) >= 2:
                results.append(
                    AutoMapFieldResult(
                        field_id=field.id,
                        field_key=field.key,
                        field_label=field_label,
                        current_question_key=field.question_key,
                        suggested_question_key=None,
                        confidence=0.0,
                        match_reason="Isolated household/secondary row (no applicant prefill)",
                        alternatives=[],
                    )
                )
                continue

            # Check Zero-PII learned curations first for high-confidence reuse
            opt_vals = [opt.value for opt in (field.options or [])]
            learned_hit = learning_service.match_field_or_choice(
                label=field_label,
                option_labels=opt_vals or None,
                source_language=latest_version.source_language or "de",
                organization_id=organization_id,
                candidates=learned_candidates,
                query_embedding=f_vec,
            )
            if (
                learned_hit
                and learned_hit[0].canonical_question_key
                and learned_hit[1] >= max(min_confidence, 0.72)
            ):
                pat, l_conf = learned_hit
                results.append(
                    AutoMapFieldResult(
                        field_id=field.id,
                        field_key=field.key,
                        field_label=field_label,
                        current_question_key=field.question_key,
                        suggested_question_key=pat.canonical_question_key,
                        confidence=round(min(1.0, l_conf), 3),
                        match_reason=f"Matched agency-curated pattern ({pat.confirmation_count}x confirmed)",
                        alternatives=[],
                    )
                )
                continue

            scored_candidates: list[tuple[CanonicalFieldDefinition, float, str]] = []

            for c_idx, candidate in enumerate(self._canonical_catalog):
                # Vector semantic similarity (0.0 to 1.0)
                v_sim = max(0.0, cosine_similarity(f_vec, canonical_vecs[c_idx]))

                # Lexical synonym matching (0.0 to 1.0)
                l_score = self._lexical_anchor_score(field_label, field.key, candidate)

                # Type compatibility (0.1 to 1.0)
                t_score = self._type_compatibility_score(
                    field.field_type, candidate.expected_type
                )

                # Combined confidence formula: 55% vector, 30% lexical, 15% type
                raw_score = (0.55 * v_sim) + (0.30 * l_score) + (0.15 * t_score)

                # If lexical exact match, boost confidence floor
                if l_score >= 0.95 and t_score >= 0.7:
                    raw_score = max(raw_score, 0.92)

                confidence = round(min(1.0, max(0.0, raw_score)), 3)

                # Build rationale
                reason = "Semantic similarity"
                if l_score >= 0.8:
                    reason = f"Exact match for term '{candidate.label_de}'"
                elif v_sim >= 0.75:
                    reason = f"High vector alignment with '{candidate.label_en}'"

                scored_candidates.append((candidate, confidence, reason))

            # Sort descending by confidence
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            top = scored_candidates[0] if scored_candidates else None
            top_key = top[0].key if top and top[1] >= min_confidence else None
            top_conf = top[1] if top and top[1] >= min_confidence else 0.0
            top_reason = (
                top[2]
                if top and top[1] >= min_confidence
                else "No confident match found"
            )

            # Alternatives (top 3 next candidates)
            alternatives = [
                AutoMapAlternative(
                    key=c[0].key,
                    label=f"{c[0].label_de} ({c[0].label_en})",
                    confidence=c[1],
                )
                for c in scored_candidates[1:4]
                if c[1] >= 0.3
            ]

            results.append(
                AutoMapFieldResult(
                    field_id=field.id,
                    field_key=field.key,
                    field_label=field_label,
                    current_question_key=field.question_key,
                    suggested_question_key=top_key,
                    confidence=top_conf,
                    match_reason=top_reason,
                    alternatives=alternatives,
                )
            )

        return results

    def apply_auto_mappings(
        self,
        organization_id: str,
        template_id: str,
        mappings: list[dict[str, Any]],
    ) -> int:
        """Applies suggested question_key mappings to form fields in the database.

        Args:
            organization_id: The tenant organization ID.
            template_id: The form template ID.
            mappings: List of dicts with 'field_id' and 'question_key'.

        Returns:
            The count of updated fields.
        """
        stmt = select(FormTemplate).where(
            FormTemplate.id == template_id,
            FormTemplate.organization_id == organization_id,
        )
        template = self.db.scalars(stmt).first()
        if not template:
            raise ResourceNotFoundError(f"Form template '{template_id}' not found.")

        v_stmt = (
            select(FormVersion)
            .where(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
        )
        latest_version = self.db.scalars(v_stmt).first()
        if not latest_version:
            raise ResourceNotFoundError("No form version found for template.")

        fields_by_id = {f.id: f for f in latest_version.fields}
        updated_count = 0

        for m in mappings:
            f_id = m.get("field_id")
            q_key = m.get("question_key")
            if f_id in fields_by_id and q_key:
                field = fields_by_id[f_id]
                field.question_key = q_key
                FormPatternLearningService(self.db).record_field_curation(
                    field,
                    source_language=latest_version.source_language or "de",
                    organization_id=organization_id,
                    scope="organization",
                )
                updated_count += 1

        if updated_count > 0:
            self.db.commit()

        return updated_count
