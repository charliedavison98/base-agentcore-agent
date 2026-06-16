import json
import logging

logger = logging.getLogger(__name__)

# Claude Sonnet 4 pricing (eu cross-region, on-demand) — USD per token
PRICING = {
    "input": 3.00 / 1_000_000,
    "output": 15.00 / 1_000_000,
    "cache_read": 0.30 / 1_000_000,
    "cache_write": 3.75 / 1_000_000,
}


def log_agent_usage(agent_result, user_id: str, thread_id: str) -> None:
    """Log structured token usage and estimated cost for a completed agent invocation."""
    if not agent_result or not hasattr(agent_result, "metrics"):
        return

    try:
        usage = agent_result.metrics.accumulated_usage
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        cache_read_tokens = usage.get("cacheReadInputTokens", 0) or 0
        cache_write_tokens = usage.get("cacheWriteInputTokens", 0) or 0

        estimated_cost = (
            input_tokens * PRICING["input"]
            + output_tokens * PRICING["output"]
            + cache_read_tokens * PRICING["cache_read"]
            + cache_write_tokens * PRICING["cache_write"]
        )

        logger.info(json.dumps({
            "event": "agent_usage",
            "user_id": user_id,
            "thread_id": thread_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        }))
    except Exception as usage_err:
        logger.warning(f"Could not log agent usage: {usage_err}")
