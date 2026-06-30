from dataclasses import dataclass

from app.models import ModelRoute, PromptVersion
from app.services.pricing import estimate_tokens


@dataclass(frozen=True)
class MockProviderResult:
    output: str
    input_tokens: int
    output_tokens: int


class MockProviderError(Exception):
    pass


class MockProviderTimeout(Exception):
    pass


def complete_with_mock_provider(
    prompt: PromptVersion,
    route: ModelRoute,
    user_input: str,
) -> MockProviderResult:
    if "[simulate_timeout]" in user_input:
        raise MockProviderTimeout("Mock provider timed out")
    if "[simulate_failure]" in user_input:
        raise MockProviderError("Mock provider failed")

    output = (
        f"[mock:{route.model_name}] "
        f"{prompt.content} "
        f"Input received: {user_input}"
    )
    return MockProviderResult(
        output=output,
        input_tokens=estimate_tokens(prompt.content) + estimate_tokens(user_input),
        output_tokens=estimate_tokens(output),
    )
