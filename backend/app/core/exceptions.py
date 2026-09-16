class LLMProviderError(Exception):
    """
    Base exception for external LLM provider failures.
    """

    def __init__(
        self,
        message: str,
        retryable: bool = False,
    ):
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class LLMRateLimitError(LLMProviderError):
    """
    Raised when the LLM provider rate/token limit
    has been exceeded.
    """

    def __init__(
        self,
        message: str = (
            "The language model provider is "
            "temporarily rate limited."
        ),
    ):
        super().__init__(
            message=message,
            retryable=True,
        )


class LLMUnavailableError(LLMProviderError):
    """
    Raised when the LLM provider cannot currently
    service requests.
    """

    def __init__(
        self,
        message: str = (
            "The language model provider is "
            "temporarily unavailable."
        ),
    ):
        super().__init__(
            message=message,
            retryable=True,
        )