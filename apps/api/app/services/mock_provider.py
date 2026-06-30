from dataclasses import dataclass

from app.models import ModelRoute, PromptVersion


@dataclass(frozen=True)
class MockProviderResult:
    output: str


def complete_with_mock_provider(
    prompt: PromptVersion,
    route: ModelRoute,
    user_input: str,
) -> MockProviderResult:
    output = (
        f"[mock:{route.model_name}] "
        f"{prompt.content} "
        f"Input received: {user_input}"
    )
    return MockProviderResult(output=output)
