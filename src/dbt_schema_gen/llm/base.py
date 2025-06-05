import abc


class LLMProvider(abc.ABC):
    """Minimal interface all concrete providers must follow."""

    @abc.abstractmethod
    def generate(self, prompt: str) -> str:  # pragma: no cover
        """Return the assistant's plain-text reply."""
