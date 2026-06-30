from decimal import Decimal, ROUND_HALF_UP

MOCK_MODEL_PRICING = {
    ("mock", "mock-llm-small"): {
        "input_per_1k": Decimal("0.000100"),
        "output_per_1k": Decimal("0.000200"),
    }
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def calculate_estimated_cost(
    provider: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    pricing = MOCK_MODEL_PRICING.get(
        (provider, model_name),
        {"input_per_1k": Decimal("0.000100"), "output_per_1k": Decimal("0.000200")},
    )
    cost = (
        Decimal(input_tokens) / Decimal(1000) * pricing["input_per_1k"]
        + Decimal(output_tokens) / Decimal(1000) * pricing["output_per_1k"]
    )
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
