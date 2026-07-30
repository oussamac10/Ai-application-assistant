"""Safe error types for the translation providers.

Every code here is *internal*. The API layer never returns one to a client:
a translation failure degrades to the fallback provider and then to the
source text, so the user sees untranslated text rather than an error. These
codes exist for logging, metrics and fallback decisions only, and must never
carry credentials, endpoint URLs, provider stack traces, raw response bodies,
or any translated text.
"""

from __future__ import annotations


class TranslationError(Exception):
    """Base class for every translation-provider failure."""


class TranslationConfigurationError(TranslationError):
    """The configured provider name is unknown, or a selected provider is
    missing required configuration."""


# Ordered roughly by how a caller should react: the first three are worth a
# retry or a fallback, the rest are not.
TRANSLATION_ERROR_CODES = (
    "translation_not_configured",
    # The endpoint answered, but not as a translation service — e.g. a
    # Document Intelligence resource URL used for Translator, which returns
    # 404 for /translate. Distinct from a transient failure because retrying
    # it is pointless and the operator needs to know it is a *configuration*
    # problem, not an outage.
    "translation_endpoint_not_found",
    "translation_authentication_failed",
    "translation_rate_limited",
    "translation_timeout",
    "translation_invalid_response",
    "translation_failed",
)

# Codes where trying again (or trying the other provider) can plausibly
# succeed. Bad credentials and a malformed request are excluded on purpose:
# retrying those just spends the timeout budget twice.
RETRYABLE_TRANSLATION_ERROR_CODES = frozenset(
    {"translation_rate_limited", "translation_timeout", "translation_failed"}
)


class TranslationProviderError(TranslationError):
    """A failure talking to, or interpreting a response from, a provider.

    `request_id` is the provider's own correlation id when the response
    carried one — kept for internal diagnostics only, never returned to a
    caller.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        request_id: str | None = None,
        request_count: int = 0,
        retry_count: int = 0,
        duration_seconds: float = 0.0,
        status_class: str = "",
    ) -> None:
        super().__init__(message)
        if error_code not in TRANSLATION_ERROR_CODES:
            raise ValueError(f"Unknown translation error code '{error_code}'.")
        self.error_code = error_code
        self.request_id = request_id
        # A failed call still costs requests and time — a retried timeout
        # sends two and burns the whole budget. Carrying that here is what
        # lets the caller report the primary provider's real cost instead of
        # attributing it to whichever provider happened to succeed.
        self.request_count = request_count
        self.retry_count = retry_count
        self.duration_seconds = duration_seconds
        self.status_class = status_class

    @property
    def is_retryable(self) -> bool:
        return self.error_code in RETRYABLE_TRANSLATION_ERROR_CODES
