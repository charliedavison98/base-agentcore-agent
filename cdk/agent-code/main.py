import logging
from typing import Any, AsyncGenerator
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from memory import get_user_preferences, store_interaction
from agent import agent
from cost_tracker import log_agent_usage

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app at module level
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload: dict[str, Any], context: RequestContext) -> AsyncGenerator[Any, None]:
    """Entrypoint for the chatbot agent with user and conversation thread support"""
    logger.info(f"Received payload: {payload}, type: {type(payload)}")

    try:
        query = payload.get("prompt", "Hello!")
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")

        thread_id = payload.get("thread_id", "default_thread")

        logger.info(f"Received query: {query}, User ID: {user_id}, Thread ID: {thread_id}")
        
        # Get user preferences context
        preferences_context = get_user_preferences(user_id)
        full_query = query + " " + preferences_context
        
        # Use module-level agent with streaming
        logger.info(f"Invoking agent with streaming query: {full_query}")
        
        # Accumulate response text for memory storage
        accumulated_text = ""
        
        # Stream events from agent
        agent_result = None
        async for event in agent.stream_async(full_query):
            # Extract text from streaming event if present
            if "data" in event:
                event_data = event["data"]
                accumulated_text += event_data
                yield event_data
            if "result" in event:
                agent_result = event["result"]
        
        # Store interaction in memory after stream completes
        logger.info(f"Stream complete. Accumulated text: {accumulated_text}")
        store_interaction(user_id, thread_id, query, accumulated_text)

        log_agent_usage(agent_result, user_id, thread_id)
    
    except Exception as e:
        logger.error(f"AgentCore runtime invocation failed: {str(e)}", exc_info=True)
        yield {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    app.run()
