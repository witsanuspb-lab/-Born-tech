from dataclasses import dataclass, field

# Pricing per million tokens (input, output) as of 2025
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8":              (15.00, 75.00),
    "claude-sonnet-4-6":            (3.00,  15.00),
    "claude-haiku-4-5":             (0.25,  1.25),
    "claude-haiku-4-5-20251001":    (0.25,  1.25),
}
_DEFAULT_PRICE = (3.00, 15.00)


@dataclass
class CostTracker:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0
    _models_seen: list = field(default_factory=list)

    def add(self, response, model: str = "claude-sonnet-4-6") -> None:
        usage = response.usage
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.calls += 1
        if model not in self._models_seen:
            self._models_seen.append(model)

    def estimated_cost(self) -> float:
        # Use the most expensive model seen (conservative estimate)
        best_price = _DEFAULT_PRICE
        for m in self._models_seen:
            p = _PRICING.get(m, _DEFAULT_PRICE)
            if p[0] > best_price[0]:
                best_price = p
        in_price, out_price = best_price
        return (self.input_tokens * in_price + self.output_tokens * out_price) / 1_000_000

    def summary(self) -> str:
        cost = self.estimated_cost()
        cache_pct = (
            round(self.cache_read_tokens / max(self.input_tokens, 1) * 100)
            if self.input_tokens else 0
        )
        return (
            f"Calls: {self.calls}  |  "
            f"In: {self.input_tokens:,}  |  "
            f"Out: {self.output_tokens:,}  |  "
            f"Cache hits: {self.cache_read_tokens:,} ({cache_pct}%)  |  "
            f"Est. cost: ${cost:.4f}"
        )

    def reset(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.calls = 0
        self._models_seen = []


# Module-level singleton
_tracker = CostTracker()


def get_tracker() -> CostTracker:
    return _tracker


def reset_tracker() -> None:
    _tracker.reset()
