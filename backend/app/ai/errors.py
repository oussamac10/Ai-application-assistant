"""AI provider error hierarchy.

All provider errors must be caught by the service layer and translated into
safe API responses.  Raw prompts, model responses, internal URLs, and stack
traces must never be exposed to callers.
"""


class AIProviderError(Exception):
    """Base class for all AI provider errors."""


class AIProviderUnavailableError(AIProviderError):
    """The provider service is unreachable (connection refused, DNS failure)."""


class AIProviderTimeoutError(AIProviderError):
    """The provider did not respond within the configured timeout."""


class AIProviderMalformedResponseError(AIProviderError):
    """The provider returned a response that is not valid JSON."""


class AIProviderValidationError(AIProviderError):
    """The provider returned JSON but it does not match the expected schema."""


class AIProviderConfigurationError(AIProviderError):
    """The provider is misconfigured (unknown provider name, missing URL, …)."""
