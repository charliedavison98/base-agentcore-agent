import os
from strands import Agent
from strands.models import BedrockModel, CacheConfig
from prompt import SYSTEM_PROMPT

# Create BedrockModel with prompt caching and guardrail enabled
bedrock_model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-6",
    cache_tools="default",  # Cache tool definitions
    cache_config=CacheConfig(strategy="auto"),  # Auto cache for multi-turn loops
    guardrail_id=os.environ.get("GUARDRAIL_ID"),
    guardrail_version=os.environ.get("GUARDRAIL_VERSION"),
    guardrail_trace="enabled",
    guardrail_stream_processing_mode="async"
)

# Create agent at module level with base system prompt
agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    name="SimpleChatbotAgent",
    model=bedrock_model,
    tools=[]
)
