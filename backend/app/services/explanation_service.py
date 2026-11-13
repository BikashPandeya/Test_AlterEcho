from app.models.schemas import MetricComparison, Site


PLANETARY_LIMITS = [
    "Earth does not reproduce Martian atmospheric pressure, reduced gravity, or radiation exposure.",
    "Terrain metrics do not measure geology, habitability, water/ice, accessibility, or operational safety.",
]


def explain(candidate: Site, metrics: list[MetricComparison], rankable: bool, coverage_ok: bool) -> tuple[str, list[str]]:
    if not rankable:
        reason = "valid coverage is below the ranking gate" if not coverage_ok else "too few comparable metrics are available"
        return f"{candidate.name} is not rankable because {reason}.", PLANETARY_LIMITS
    strongest = max(metrics, key=lambda item: item.similarity)
    explanation = (
        f"{candidate.name} is most similar under the selected terrain metrics in "
        f"{strongest.metric.replace('_', ' ')}. This is a partial terrain analogy, not an overall Mars match."
    )
    return explanation, PLANETARY_LIMITS

