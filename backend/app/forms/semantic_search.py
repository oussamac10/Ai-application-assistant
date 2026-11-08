"""Multilingual Semantic Form Search Service.

Allows citizens to discover German municipal administrative forms using natural language
queries in any of the 8 supported languages (English, Arabic, Turkish, Ukrainian, French, etc.)
via cross-lingual vector embeddings and semantic similarity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding.factory import get_embedding_provider
from app.ai.embedding.protocol import EmbeddingProvider
from app.ai.embedding.similarity import cosine_similarity
from app.forms.auto_mapper import get_field_primary_label
from app.forms.models import FormTemplate, FormVersion
from app.organizations.models import Organization

logger = logging.getLogger(__name__)


@dataclass
class FormSearchResultItem:
    template_id: str
    key: str
    title: str
    description: str | None
    category_slug: str | None
    category_name: str | None
    relevance_score: float
    match_type: str
    matched_reason: str


class MultilingualSemanticSearchService:
    """Provides cross-lingual semantic search over published organization forms."""

    def __init__(
        self,
        db: Session,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.db = db
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self._form_embedding_cache: dict[str, list[float]] = {}

    def _build_form_search_corpus(
        self, template: FormTemplate, version: FormVersion
    ) -> str:
        """Constructs rich multilingual semantic text representation for a form."""
        parts = [
            template.name or "",
            template.description or "",
            template.category or "",
            template.instructions or "",
        ]
        # Include top field labels
        for f in version.fields[:15]:
            label = get_field_primary_label(f, version.source_language)
            if label:
                parts.append(label)

        return " ".join(p.strip() for p in parts if p.strip())

    async def search_organization_forms(
        self,
        organization_slug: str,
        query: str,
        limit: int = 10,
        min_score: float = 0.25,
    ) -> list[FormSearchResultItem]:
        """Performs semantic search across published forms of an organization."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        # 1. Fetch organization
        org_stmt = select(Organization).where(Organization.slug == organization_slug)
        org = self.db.scalars(org_stmt).first()
        if not org:
            return []

        # 2. Fetch all templates for this organization
        stmt = select(FormTemplate).where(FormTemplate.organization_id == org.id)
        templates = self.db.scalars(stmt).all()
        if not templates:
            return []

        # 3. Load latest version for each template
        form_data: list[tuple[FormTemplate, FormVersion, str]] = []
        for t in templates:
            v_stmt = (
                select(FormVersion)
                .where(FormVersion.form_template_id == t.id)
                .order_by(FormVersion.version_number.desc())
            )
            v = self.db.scalars(v_stmt).first()
            if v and v.status == "published":
                corpus = self._build_form_search_corpus(t, v)
                form_data.append((t, v, corpus))

        if not form_data:
            return []

        # 4. Generate embeddings for query and form corpus
        query_vec = await self.embedding_provider.get_embedding(cleaned_query)

        results: list[FormSearchResultItem] = []
        q_lower = cleaned_query.lower()

        for template, version, corpus in form_data:
            cache_key = f"{template.id}:{version.id}"
            if cache_key in self._form_embedding_cache:
                doc_vec = self._form_embedding_cache[cache_key]
            else:
                doc_vec = await self.embedding_provider.get_embedding(corpus)
                self._form_embedding_cache[cache_key] = doc_vec

            # Cosine semantic similarity
            v_sim = max(0.0, cosine_similarity(query_vec, doc_vec))

            # Fast lexical exact match boost
            c_lower = corpus.lower()
            t_lower = (template.name or "").lower()
            exact_hit = q_lower in t_lower or q_lower in c_lower

            # Compute composite score
            score = v_sim
            match_type = "semantic"
            reason = "Semantic relevance"

            if exact_hit:
                score = max(score, 0.88)
                match_type = "exact"
                reason = "Direct keyword match"
            elif any(word in t_lower for word in q_lower.split() if len(word) > 2):
                score = max(score, 0.70)
                match_type = "keyword"
                reason = "Partial keyword match"

            if score >= min_score:
                results.append(
                    FormSearchResultItem(
                        template_id=template.id,
                        key=template.key,
                        title=template.name,
                        description=template.description,
                        category_slug=template.category,
                        category_name=template.category_rel.name
                        if template.category_rel
                        else None,
                        relevance_score=round(score, 3),
                        match_type=match_type,
                        matched_reason=reason,
                    )
                )

        # Sort descending by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]
