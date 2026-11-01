import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import AIUsageEvent

logger = logging.getLogger(__name__)

# Hard cost cap per candidate session (EUR 0.25) to protect >85% margins
MAX_SESSION_COST_EUR: float = 0.25

# Estimated costs per unit for COGS monitoring
GEMINI_INPUT_PER_1K_EUR = 0.000075
GEMINI_OUTPUT_PER_1K_EUR = 0.000300
AZURE_DOC_INTEL_PER_PAGE_EUR = 0.010000
AZURE_TRANSLATOR_PER_CHAR_EUR = 0.000010


def calculate_llm_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates approximate EUR cost for LLM calls based on token counts."""
    input_cost = (prompt_tokens / 1000.0) * GEMINI_INPUT_PER_1K_EUR
    output_cost = (completion_tokens / 1000.0) * GEMINI_OUTPUT_PER_1K_EUR
    return round(input_cost + output_cost, 6)


def record_ai_usage(
    db: Session,
    *,
    provider: str,
    operation: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_eur: float | None = None,
    session_id: str | None = None,
    case_id: str | None = None,
    organization_id: str | None = None,
) -> AIUsageEvent:
    """Records an AI or cloud API invocation into the audit ledger."""
    if cost_eur is None:
        cost_eur = calculate_llm_cost(prompt_tokens, completion_tokens)

    event = AIUsageEvent(
        provider=provider,
        operation=operation,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_eur=cost_eur,
        session_id=session_id,
        case_id=case_id,
        organization_id=organization_id,
    )
    db.add(event)
    db.flush()
    return event


def get_session_cumulative_cost(db: Session, session_id: str) -> float:
    """Returns the total accumulated API spend in EUR for a specific session."""
    stmt = select(func.coalesce(func.sum(AIUsageEvent.cost_eur), 0.0)).where(
        AIUsageEvent.session_id == session_id
    )
    total: float = db.execute(stmt).scalar() or 0.0
    return float(total)


def is_session_budget_exceeded(
    db: Session,
    session_id: str,
    *,
    limit_eur: float = MAX_SESSION_COST_EUR,
) -> bool:
    """Checks whether the session has reached the hard circuit breaker limit."""
    total = get_session_cumulative_cost(db, session_id)
    if total >= limit_eur:
        logger.warning(
            "Session %s reached spend limit: €%.4f >= €%.4f. Activating deterministic fallback.",
            session_id,
            total,
            limit_eur,
        )
        return True
    return False
