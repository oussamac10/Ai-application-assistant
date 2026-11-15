"""Zero-PII continual schema learning service for tables, choice groups, and fields."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.ai.embedding.factory import get_embedding_provider
from app.ai.embedding.similarity import cosine_similarity
from app.forms.learning_models import LearnedFormPattern
from app.forms.models import FormField, FormVersion

if TYPE_CHECKING:
    from app.ai.embedding.protocol import EmbeddingProvider

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LONG_DIGITS_RE = re.compile(r"\d[\d\s\-/]{7,}\d")
_LEADING_ITEM_NUM_RE = re.compile(r"^\s*(?:\[\d+\]|\(?\d+[.)]?)\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def sanitize_structural_text(raw: str | None, max_len: int = 240) -> str:
    """Strip PII-looking tokens and form item prefixes from schema labels."""
    if not raw:
        return ""
    cleaned = _LEADING_ITEM_NUM_RE.sub("", str(raw).strip())
    cleaned = _EMAIL_RE.sub("", cleaned)
    cleaned = _LONG_DIGITS_RE.sub("", cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].strip()
    return cleaned


def fold_tokens(raw: str | None) -> list[str]:
    """Normalize text into comparable ASCII/Unicode word tokens."""
    sanitized = sanitize_structural_text(raw)
    if not sanitized:
        return []
    decomposed = unicodedata.normalize("NFKD", sanitized)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = stripped.replace("ı", "i").replace("ß", "ss").lower()
    stripped = _NON_WORD_RE.sub(" ", stripped)
    return [tok for tok in stripped.split() if tok and not tok.isdigit()]


def build_signature(
    label: str | None,
    extra_parts: list[str] | None = None,
) -> tuple[str, str, list[str]]:
    """Return `(signature_hash, normalized_signature, raw_tokens)` for a schema item."""
    label_tokens = fold_tokens(label)
    extra_tokens: list[str] = []
    part_sigs: list[str] = []
    for part in extra_parts or []:
        t = fold_tokens(part)
        if t:
            extra_tokens.extend(t)
            part_sigs.append(" ".join(t))

    base = " ".join(label_tokens)
    if part_sigs:
        normalized_sig = f"{base}||{'|'.join(sorted(set(part_sigs)))}"
    else:
        normalized_sig = base

    raw_tokens = list(dict.fromkeys([*label_tokens, *extra_tokens]))
    digest = hashlib.sha256(normalized_sig.encode("utf-8")).hexdigest()
    return digest, normalized_sig, raw_tokens


def build_table_signature(
    column_headers: list[str],
    table_title: str | None = None,
) -> tuple[str, str, list[str]]:
    """Build an ordered column-header signature for repeatable table schemas."""
    ordered_cols: list[str] = []
    all_tokens: list[str] = []
    for header in column_headers:
        toks = fold_tokens(header)
        if toks:
            ordered_cols.append(" ".join(toks))
            all_tokens.extend(toks)
    for title_tok in fold_tokens(table_title):
        all_tokens.append(title_tok)

    normalized_sig = "|".join(ordered_cols)
    raw_tokens = list(dict.fromkeys(all_tokens))
    digest = hashlib.sha256(normalized_sig.encode("utf-8")).hexdigest()
    return digest, normalized_sig, raw_tokens


def _jaccard(tokens_a: list[str], tokens_b: list[str]) -> float:
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


def _extract_field_translations(
    field: FormField, source_language: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for tr in field.translations or []:
        label = sanitize_structural_text(tr.label)
        if not label:
            continue
        entry: dict[str, Any] = {"label": label}
        if tr.help_text:
            help_clean = sanitize_structural_text(tr.help_text, max_len=500)
            if help_clean:
                entry["help_text"] = help_clean
        if tr.placeholder:
            ph_clean = sanitize_structural_text(tr.placeholder, max_len=160)
            if ph_clean:
                entry["placeholder"] = ph_clean
        result[tr.language] = entry
    if not result and field.key:
        result[source_language] = {
            "label": sanitize_structural_text(field.key.replace("_", " "))
        }
    return result


def _extract_field_options(
    field: FormField, source_language: str
) -> list[dict[str, Any]] | None:
    opts = []
    for opt in field.options or []:
        val = sanitize_structural_text(opt.value, max_len=120)
        if not val:
            continue
        tr_map: dict[str, str] = {}
        for ot in opt.translations or []:
            lbl = sanitize_structural_text(ot.label, max_len=160)
            if lbl:
                tr_map[ot.language] = lbl
        if not tr_map:
            tr_map[source_language] = val
        opts.append({"value": val, "translations": tr_map})
    if opts:
        return opts

    cfg_opts = (
        (field.configuration or {}).get("options")
        if isinstance(field.configuration, dict)
        else None
    )
    if isinstance(cfg_opts, list):
        fallback: list[dict[str, Any]] = []
        for item in cfg_opts:
            if not isinstance(item, dict):
                continue
            val = sanitize_structural_text(str(item.get("value") or ""), max_len=120)
            lbl = sanitize_structural_text(str(item.get("label") or val), max_len=160)
            if val:
                fallback.append(
                    {"value": val, "translations": {source_language: lbl or val}}
                )
        return fallback or None
    return None


def _is_secondary_table_row(field: FormField) -> bool:
    """Return True if field belongs to table row 2+ (must never receive applicant Vault keys)."""
    cfg = field.configuration if isinstance(field.configuration, dict) else {}
    tbl = cfg.get("table") if isinstance(cfg, dict) else None
    if isinstance(tbl, dict) and tbl.get("row_index") is not None:
        return int(tbl["row_index"]) >= 2
    return False


class FormPatternLearningService:
    """Captures and matches Zero-PII structural curations from agencies & admins."""

    def __init__(
        self,
        db: Session,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self.embedding_provider = embedding_provider

    async def compute_embedding_async(self, text: str) -> list[float] | None:
        """Compute embedding asynchronously for optional semantic pattern recall."""
        if not text:
            return None
        provider = self.embedding_provider
        if provider is None:
            try:
                provider = get_embedding_provider()
            except Exception:
                return None
        try:
            vec = await provider.get_embedding(text)
            return [float(x) for x in vec] if vec else None
        except Exception:
            logger.debug("Optional async embedding failed; lexical matching active.")
            return None

    def _upsert_pattern(
        self,
        *,
        pattern_type: str,
        signature_hash: str,
        normalized_signature: str,
        raw_header_tokens: list[str],
        source_language: str,
        canonical_field_type: str,
        canonical_question_key: str | None,
        canonical_requiredness: str,
        canonical_options_json: list[dict[str, Any]] | None,
        table_structure_json: dict[str, Any] | None,
        translations_json: dict[str, dict[str, Any]] | None,
        source_organization_id: str | None,
        scope: str,
        embedding: list[float] | None = None,
    ) -> LearnedFormPattern | None:
        if not normalized_signature or not raw_header_tokens:
            return None

        existing = (
            self.db.query(LearnedFormPattern)
            .filter(
                LearnedFormPattern.pattern_type == pattern_type,
                LearnedFormPattern.signature_hash == signature_hash,
                LearnedFormPattern.source_organization_id == source_organization_id,
            )
            .first()
        )
        now = datetime.now(UTC)
        if existing:
            existing.confirmation_count = int(existing.confirmation_count or 1) + 1
            existing.last_confirmed_at = now
            existing.canonical_field_type = canonical_field_type
            if canonical_question_key is not None:
                existing.canonical_question_key = canonical_question_key
            if canonical_requiredness and canonical_requiredness != "unknown":
                existing.canonical_requiredness = canonical_requiredness
            if canonical_options_json:
                existing.canonical_options_json = canonical_options_json
            if table_structure_json:
                existing.table_structure_json = table_structure_json
            if translations_json:
                merged = dict(existing.translations_json or {})
                merged.update(translations_json)
                existing.translations_json = merged
            if scope == "global":
                existing.scope = "global"
            if existing.embedding_json is None and embedding is not None:
                existing.embedding_json = embedding
            self.db.add(existing)
            return existing

        pattern = LearnedFormPattern(
            source_organization_id=source_organization_id,
            scope=scope,
            pattern_type=pattern_type,
            signature_hash=signature_hash,
            source_language=source_language or "de",
            normalized_signature=normalized_signature,
            raw_header_tokens=raw_header_tokens,
            canonical_field_type=canonical_field_type,
            canonical_question_key=canonical_question_key,
            canonical_requiredness=canonical_requiredness or "unknown",
            canonical_options_json=canonical_options_json,
            table_structure_json=table_structure_json,
            translations_json=translations_json,
            embedding_json=embedding,
            confirmation_count=1,
            last_confirmed_at=now,
        )
        self.db.add(pattern)
        return pattern

    def record_field_curation(
        self,
        field: FormField,
        *,
        source_language: str,
        organization_id: str | None,
        scope: str = "organization",
        embedding: list[float] | None = None,
    ) -> LearnedFormPattern | None:
        """Record a Zero-PII curated field or choice-group pattern from a FormField."""
        translations = _extract_field_translations(field, source_language)
        src_entry = translations.get(source_language) or next(
            iter(translations.values()), None
        )
        label = (src_entry or {}).get("label") or field.key
        options = _extract_field_options(field, source_language)

        is_choice = field.field_type in (
            "single_choice",
            "multiple_choice",
            "choice",
        ) and bool(options)
        pattern_type = "choice_group" if is_choice else "field"
        option_labels = [opt["value"] for opt in (options or [])]
        sig_hash, norm_sig, raw_tokens = build_signature(
            label,
            extra_parts=option_labels if is_choice else None,
        )

        # Never leak primary applicant Vault keys from secondary household member rows
        q_key = None if _is_secondary_table_row(field) else field.question_key
        req = field.requiredness or ("required" if field.required else "unknown")

        return self._upsert_pattern(
            pattern_type=pattern_type,
            signature_hash=sig_hash,
            normalized_signature=norm_sig,
            raw_header_tokens=raw_tokens,
            source_language=source_language,
            canonical_field_type=field.field_type,
            canonical_question_key=q_key,
            canonical_requiredness=req,
            canonical_options_json=options,
            table_structure_json=None,
            translations_json=translations,
            source_organization_id=organization_id,
            scope=scope,
            embedding=embedding,
        )

    def record_choice_group_curation(
        self,
        *,
        label: str,
        options: list[dict[str, Any]],
        source_language: str,
        field_type: str,
        translations: dict[str, dict[str, Any]] | None,
        organization_id: str | None,
        scope: str = "organization",
        question_key: str | None = None,
        requiredness: str = "unknown",
        embedding: list[float] | None = None,
    ) -> LearnedFormPattern | None:
        """Explicitly record a curated multi-checkbox choice group."""
        clean_label = sanitize_structural_text(label)
        option_vals = [
            sanitize_structural_text(str(o.get("value") or ""))
            for o in options
            if o.get("value")
        ]
        sig_hash, norm_sig, raw_tokens = build_signature(
            clean_label,
            extra_parts=option_vals,
        )
        return self._upsert_pattern(
            pattern_type="choice_group",
            signature_hash=sig_hash,
            normalized_signature=norm_sig,
            raw_header_tokens=raw_tokens,
            source_language=source_language,
            canonical_field_type=field_type,
            canonical_question_key=question_key,
            canonical_requiredness=requiredness,
            canonical_options_json=options,
            table_structure_json=None,
            translations_json=translations,
            source_organization_id=organization_id,
            scope=scope,
            embedding=embedding,
        )

    def record_table_schema_curation(
        self,
        *,
        table_key: str,
        table_title: str | None,
        row_fields_by_index: dict[int, list[FormField]],
        source_language: str,
        organization_id: str | None,
        scope: str = "organization",
        embedding: list[float] | None = None,
    ) -> LearnedFormPattern | None:
        """Record a Zero-PII table schema pattern based on its first row's columns."""
        if not row_fields_by_index:
            return None
        first_idx = min(row_fields_by_index.keys())
        first_row = sorted(
            row_fields_by_index[first_idx],
            key=lambda item: (
                int(
                    (item.configuration or {})
                    .get("table", {})
                    .get("col_index", item.position)
                ),
                item.position,
            ),
        )
        if not first_row:
            return None

        col_headers: list[str] = []
        columns_meta: list[dict[str, Any]] = []
        for idx, rf in enumerate(first_row):
            tbl = (rf.configuration or {}).get("table") or {}
            tr = _extract_field_translations(rf, source_language)
            src_tr = tr.get(source_language) or next(iter(tr.values()), None)
            header = sanitize_structural_text(
                str(tbl.get("column_header") or (src_tr or {}).get("label") or rf.key)
            )
            col_headers.append(header)
            columns_meta.append(
                {
                    "col_index": int(tbl.get("col_index", idx)),
                    "header": header,
                    "field_type": rf.field_type,
                    "question_key": rf.question_key if first_idx == 1 else None,
                    "requiredness": rf.requiredness
                    or ("required" if rf.required else "unknown"),
                    "options": _extract_field_options(rf, source_language),
                    "translations": tr,
                }
            )

        clean_title = sanitize_structural_text(
            table_title or table_key.replace("_", " ")
        )
        sig_hash, norm_sig, raw_tokens = build_table_signature(
            col_headers, table_title=clean_title
        )
        table_struct = {
            "table_title": clean_title,
            "columns": columns_meta,
            "row1_role": "applicant",
            "other_rows_role": "member",
        }
        return self._upsert_pattern(
            pattern_type="table_schema",
            signature_hash=sig_hash,
            normalized_signature=norm_sig,
            raw_header_tokens=raw_tokens,
            source_language=source_language,
            canonical_field_type="table_group",
            canonical_question_key=None,
            canonical_requiredness="unknown",
            canonical_options_json=None,
            table_structure_json=table_struct,
            translations_json={source_language: {"label": clean_title}}
            if clean_title
            else None,
            source_organization_id=organization_id,
            scope=scope,
            embedding=embedding,
        )

    def record_published_version(
        self,
        version: FormVersion,
        *,
        source_language: str,
        organization_id: str | None,
        promote_global: bool = False,
    ) -> int:
        """Capture curated fields, choices, and table schemas when a version is published."""
        scope = "global" if promote_global else "organization"
        recorded = 0
        tables_grouped: dict[str, dict[int, list[FormField]]] = {}
        table_titles: dict[str, str] = {}

        for field in version.fields or []:
            cfg = field.configuration if isinstance(field.configuration, dict) else {}
            tbl = cfg.get("table") if isinstance(cfg, dict) else None
            if (
                isinstance(tbl, dict)
                and tbl.get("table_key")
                and tbl.get("row_index") is not None
            ):
                t_key = str(tbl["table_key"])
                r_idx = int(tbl["row_index"])
                tables_grouped.setdefault(t_key, {}).setdefault(r_idx, []).append(field)
                if t_key not in table_titles and tbl.get("table_title"):
                    table_titles[t_key] = str(tbl["table_title"])

            if (
                field.field_type in ("single_choice", "multiple_choice", "choice")
                or field.question_key
                or field.requiredness in ("required", "optional")
            ):
                if self.record_field_curation(
                    field,
                    source_language=source_language,
                    organization_id=organization_id,
                    scope=scope,
                ):
                    recorded += 1

        for t_key, rows_map in tables_grouped.items():
            if self.record_table_schema_curation(
                table_key=t_key,
                table_title=table_titles.get(t_key),
                row_fields_by_index=rows_map,
                source_language=source_language,
                organization_id=organization_id,
                scope=scope,
            ):
                recorded += 1

        return recorded

    def load_candidates(
        self,
        organization_id: str | None,
        source_language: str | None = None,
        limit: int = 500,
    ) -> list[LearnedFormPattern]:
        """Preload relevant organization + global patterns ordered by confirmation weight."""
        query = self.db.query(LearnedFormPattern)
        if organization_id:
            query = query.filter(
                or_(
                    LearnedFormPattern.source_organization_id == organization_id,
                    LearnedFormPattern.scope == "global",
                )
            )
        else:
            query = query.filter(LearnedFormPattern.scope == "global")

        if source_language:
            query = query.order_by(
                desc(LearnedFormPattern.source_language == source_language),
                desc(LearnedFormPattern.confirmation_count),
                desc(LearnedFormPattern.last_confirmed_at),
            )
        else:
            query = query.order_by(
                desc(LearnedFormPattern.confirmation_count),
                desc(LearnedFormPattern.last_confirmed_at),
            )
        return query.limit(limit).all()

    def _score_candidate(
        self,
        pat: LearnedFormPattern,
        sig_hash: str,
        tokens: list[str],
        query_emb: list[float] | None,
    ) -> float:
        if pat.signature_hash == sig_hash:
            return 1.0
        jac = _jaccard(tokens, list(pat.raw_header_tokens or []))
        if jac >= 0.72:
            return jac
        if query_emb and pat.embedding_json:
            cos = cosine_similarity(query_emb, [float(x) for x in pat.embedding_json])
            if cos >= 0.80:
                return cos
        return 0.0

    def match_field_or_choice(
        self,
        label: str,
        option_labels: list[str] | None,
        source_language: str,
        organization_id: str | None = None,
        candidates: list[LearnedFormPattern] | None = None,
        query_embedding: list[float] | None = None,
    ) -> tuple[LearnedFormPattern, float] | None:
        """Match a field/choice label (+ optional option labels) against learned patterns."""
        pool = (
            candidates
            if candidates is not None
            else self.load_candidates(organization_id, source_language)
        )
        field_pool = [p for p in pool if p.pattern_type in ("choice_group", "field")]
        if not field_pool:
            return None

        sig_hash_with_opts, _norm_opts, tokens_with_opts = build_signature(
            label, extra_parts=option_labels
        )
        sig_hash_label, _norm_lbl, tokens_label = build_signature(label, None)

        best: tuple[LearnedFormPattern, float] | None = None
        for pat in field_pool:
            score = max(
                self._score_candidate(
                    pat, sig_hash_with_opts, tokens_with_opts, query_embedding
                ),
                self._score_candidate(
                    pat, sig_hash_label, tokens_label, query_embedding
                ),
            )
            if score > 0 and (
                best is None
                or score > best[1]
                or (
                    score == best[1]
                    and pat.source_organization_id == organization_id
                    and best[0].source_organization_id != organization_id
                )
            ):
                best = (pat, score)

        return best

    def match_table_schema(
        self,
        column_headers: list[str],
        table_title: str | None,
        source_language: str,
        organization_id: str | None = None,
        candidates: list[LearnedFormPattern] | None = None,
        query_embedding: list[float] | None = None,
    ) -> tuple[LearnedFormPattern, float] | None:
        """Match a detected table schema by its column headers."""
        pool = (
            candidates
            if candidates is not None
            else self.load_candidates(organization_id, source_language)
        )
        table_pool = [p for p in pool if p.pattern_type == "table_schema"]
        if not table_pool or not column_headers:
            return None

        sig_hash, _norm_sig, tokens = build_table_signature(
            column_headers, table_title=table_title
        )
        best: tuple[LearnedFormPattern, float] | None = None

        for pat in table_pool:
            if pat.signature_hash == sig_hash:
                score = 1.0
            else:
                pat_cols = [
                    str(c.get("header") or "")
                    for c in ((pat.table_structure_json or {}).get("columns") or [])
                    if isinstance(c, dict)
                ]
                pat_col_tokens = [tok for h in pat_cols for tok in fold_tokens(h)]
                col_tokens = [tok for h in column_headers for tok in fold_tokens(h)]
                score = max(
                    _jaccard(col_tokens, pat_col_tokens),
                    _jaccard(tokens, list(pat.raw_header_tokens or [])),
                )
                if score < 0.65 and query_embedding and pat.embedding_json:
                    cos = cosine_similarity(
                        query_embedding, [float(x) for x in pat.embedding_json]
                    )
                    score = cos if cos >= 0.80 else 0.0
                elif score < 0.65:
                    score = 0.0

            if score > 0 and (best is None or score > best[1]):
                best = (pat, score)

        return best

    def enrich_extracted_fields(
        self,
        extracted_fields: list[dict[str, Any]],
        *,
        source_language: str,
        organization_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Apply learned table, choice-group, and field patterns to extracted fields."""
        candidates = self.load_candidates(organization_id, source_language)
        if not candidates or not extracted_fields:
            return extracted_fields

        tables: dict[str, dict[int, list[dict[str, Any]]]] = {}
        table_titles: dict[str, str | None] = {}
        for f in extracted_fields:
            tbl = f.get("table")
            if (
                isinstance(tbl, dict)
                and tbl.get("table_key")
                and tbl.get("row_index") is not None
            ):
                t_key = str(tbl["table_key"])
                r_idx = int(tbl["row_index"])
                tables.setdefault(t_key, {}).setdefault(r_idx, []).append(f)
                if t_key not in table_titles:
                    table_titles[t_key] = tbl.get("table_title")

        for t_key, rows_map in tables.items():
            first_idx = min(rows_map.keys())
            first_row = sorted(
                rows_map[first_idx],
                key=lambda item: int((item.get("table") or {}).get("col_index", 0)),
            )
            col_headers = [
                str(
                    (item.get("table") or {}).get("column_header")
                    or item.get("label")
                    or ""
                )
                for item in first_row
            ]
            matched_table = self.match_table_schema(
                column_headers=col_headers,
                table_title=table_titles.get(t_key),
                source_language=source_language,
                organization_id=organization_id,
                candidates=candidates,
            )
            if not matched_table:
                continue

            pat, score = matched_table
            cols_meta = (pat.table_structure_json or {}).get("columns") or []
            cols_by_idx = {
                int(c["col_index"]): c
                for c in cols_meta
                if isinstance(c, dict) and "col_index" in c
            }
            for r_idx, r_fields in rows_map.items():
                for rf in r_fields:
                    c_idx = int((rf.get("table") or {}).get("col_index", 0))
                    c_meta = cols_by_idx.get(c_idx)
                    if not c_meta:
                        continue
                    if c_meta.get("field_type"):
                        rf["field_type"] = c_meta["field_type"]
                    if (
                        c_meta.get("requiredness")
                        and c_meta["requiredness"] != "unknown"
                    ):
                        rf["requiredness"] = c_meta["requiredness"]
                    if (
                        r_idx == 1
                        and c_meta.get("question_key")
                        and not rf.get("question_key")
                    ):
                        rf["question_key"] = c_meta["question_key"]
                    elif r_idx >= 2:
                        rf["question_key"] = None
                    if c_meta.get("options") and not rf.get("options"):
                        rf["options"] = c_meta["options"]
                    if c_meta.get("translations"):
                        rf["learned_translations"] = c_meta["translations"]
                    rf["learned_pattern_id"] = pat.id
                    rf["learned_confidence"] = round(float(score), 3)

        for f in extracted_fields:
            if f.get("learned_pattern_id"):
                continue
            label = str(f.get("label") or "")
            raw_opts = f.get("options") or []
            opt_labels = [
                str(o.get("value") or o.get("label") or "")
                if isinstance(o, dict)
                else str(o)
                for o in raw_opts
                if (isinstance(o, dict) and (o.get("value") or o.get("label")))
                or isinstance(o, str)
            ]
            matched = self.match_field_or_choice(
                label=label,
                option_labels=opt_labels or None,
                source_language=source_language,
                organization_id=organization_id,
                candidates=candidates,
            )
            if not matched:
                continue

            pat, score = matched
            tbl = f.get("table")
            is_secondary_row = (
                isinstance(tbl, dict) and int(tbl.get("row_index") or 1) >= 2
            )
            if pat.canonical_field_type:
                f["field_type"] = pat.canonical_field_type
            if pat.canonical_requiredness and pat.canonical_requiredness != "unknown":
                f["requiredness"] = pat.canonical_requiredness
            if (
                not is_secondary_row
                and pat.canonical_question_key
                and not f.get("question_key")
            ):
                f["question_key"] = pat.canonical_question_key
            elif is_secondary_row:
                f["question_key"] = None
            if pat.canonical_options_json and not f.get("options"):
                f["options"] = pat.canonical_options_json
            if pat.translations_json:
                f["learned_translations"] = pat.translations_json
            f["learned_pattern_id"] = pat.id
            f["learned_confidence"] = round(float(score), 3)

        return extracted_fields
