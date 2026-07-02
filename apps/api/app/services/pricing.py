"""Token and cost helpers for gateway usage attribution.

The current pricing table is intentionally small and mock-provider focused.
When a real provider is added, this module should be updated with the provider's
current token accounting and model prices.
"""

from decimal import ROUND_HALF_UP, Decimal

MOCK_MODEL_PRICING = {
    ("mock", "mock-llm-small"): {
        "input_per_1k": Decimal("0.000100"),
        "output_per_1k": Decimal("0.000200"),
    }
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens for local mock usage.

    This is not a production tokenizer. It is a lightweight approximation that
    keeps local cost and dashboard behavior deterministic.
    """
    return max(1, len(text.split()))


def calculate_estimated_cost(
    provider: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """Calculate estimated request cost from provider/model token prices."""
    pricing = MOCK_MODEL_PRICING.get(
        (provider, model_name),
        {"input_per_1k": Decimal("0.000100"), "output_per_1k": Decimal("0.000200")},
    )
    cost = (
        Decimal(input_tokens) / Decimal(1000) * pricing["input_per_1k"]
        + Decimal(output_tokens) / Decimal(1000) * pricing["output_per_1k"]
    )
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
