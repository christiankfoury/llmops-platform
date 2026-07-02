"""Local provider adapter used before real paid provider integration.

The mock adapter lets the gateway exercise routing, retries, persistence,
metrics, and dashboard behavior without needing OpenAI credentials or spending
money. It also provides deterministic failure triggers for tests and demos.
"""

from dataclasses import dataclass

from app.models import ModelRoute, PromptVersion
from app.services.pricing import estimate_tokens


@dataclass(frozen=True)
class MockProviderResult:
    """Provider-shaped response returned by the local mock adapter."""

    output: str
    input_tokens: int
    output_tokens: int


class MockProviderError(Exception):
    """Raised when the mock provider simulates a provider-side failure."""

    pass


class MockProviderTimeout(Exception):
    """Raised when the mock provider simulates a timeout."""

    pass


def complete_with_mock_provider(
    prompt: PromptVersion,
    route: ModelRoute,
    user_input: str,
    attempt: int = 1,
) -> MockProviderResult:
    """Return a deterministic mock completion for the selected prompt and route.

    Special marker strings in `user_input` intentionally simulate provider
    failures. Tests use these markers to verify that gateway failures are
    recorded and surfaced correctly.
    """
    if "[simulate_timeout]" in user_input:
        raise MockProviderTimeout("Mock provider timed out")
    if "[simulate_transient_failure]" in user_input and attempt == 1:
        raise MockProviderError("Mock provider transient failure")
    if "[simulate_failure]" in user_input:
        raise MockProviderError("Mock provider failed")

    output = f"[mock:{route.model_name}] {prompt.content} Input received: {user_input}"
    return MockProviderResult(
        output=output,
        input_tokens=estimate_tokens(prompt.content) + estimate_tokens(user_input),
        output_tokens=estimate_tokens(output),
    )
