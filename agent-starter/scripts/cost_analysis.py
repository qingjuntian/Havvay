"""Project model usage and cost for a representative request mix."""

from dataclasses import dataclass
import argparse
import json
import os
from typing import Dict, List


@dataclass(frozen=True)
class RequestProfile:
    name: str
    requests: int
    prompt_tokens: int
    completion_tokens: int
    cache_hit_rate: float = 0.0


def analyze_cost(
    profiles: List[RequestProfile],
    input_cost_per_1m: float,
    output_cost_per_1m: float,
) -> Dict:
    if input_cost_per_1m < 0 or output_cost_per_1m < 0:
        raise ValueError("Token prices cannot be negative")

    total_requests = sum(profile.requests for profile in profiles)
    total_cost = 0.0
    uncached_cost = 0.0
    drivers = []

    for profile in profiles:
        if profile.requests < 0 or profile.prompt_tokens < 0 or profile.completion_tokens < 0:
            raise ValueError("Request counts and token counts cannot be negative")
        if not 0 <= profile.cache_hit_rate <= 1:
            raise ValueError("cache_hit_rate must be between 0 and 1")

        uncached_profile_cost = profile.requests * (
            profile.prompt_tokens * input_cost_per_1m
            + profile.completion_tokens * output_cost_per_1m
        ) / 1_000_000
        profile_cost = uncached_profile_cost * (1 - profile.cache_hit_rate)
        uncached_cost += uncached_profile_cost
        total_cost += profile_cost
        drivers.append({"name": profile.name, "cost_usd": round(profile_cost, 8)})

    drivers.sort(key=lambda item: item["cost_usd"], reverse=True)
    return {
        "requests": total_requests,
        "cost_usd": round(total_cost, 8),
        "uncached_cost_usd": round(uncached_cost, 8),
        "cache_savings_usd": round(uncached_cost - total_cost, 8),
        "average_cost_per_request_usd": round(total_cost / total_requests, 8) if total_requests else 0.0,
        "hot_paths": drivers,
    }


def default_profiles(requests: int) -> List[RequestProfile]:
    follow_up_requests = requests // 5
    calculator_requests = requests // 10
    return [
        RequestProfile(
            "model_queries",
            requests - follow_up_requests - calculator_requests,
            900,
            300,
            0.25,
        ),
        RequestProfile("follow_up_queries", follow_up_requests, 1200, 350, 0.10),
        RequestProfile("calculator_tool", calculator_requests, 0, 0, 0.0),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument(
        "--input-cost-per-1m",
        type=float,
        default=float(os.getenv("MOONSHOT_INPUT_COST_PER_1M_TOKENS", "0")),
    )
    parser.add_argument(
        "--output-cost-per-1m",
        type=float,
        default=float(os.getenv("MOONSHOT_OUTPUT_COST_PER_1M_TOKENS", "0")),
    )
    args = parser.parse_args()
    if args.requests < 0:
        parser.error("--requests cannot be negative")
    print(json.dumps(analyze_cost(default_profiles(args.requests), args.input_cost_per_1m, args.output_cost_per_1m), indent=2))


if __name__ == "__main__":
    main()
