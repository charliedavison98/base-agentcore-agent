import logging
import os
from bedrock_agentcore.memory import MemoryClient

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize memory client at module level
MEMORY_ID = os.environ.get("MEMORY_ID")
memory_client = MemoryClient(
    region_name=os.environ.get("AWS_DEFAULT_REGION")
)

def get_user_preferences(user_id: str) -> str:
    """Retrieve extracted user preferences from long-term memory"""
    if not memory_client or not MEMORY_ID:
        return ""

    try:
        logger.info(f"Getting user preferences for user ID: {user_id}")
        memories = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/chatbot/{user_id}/preferences/",
            query="preferences interests conversation style topics",
            top_k=10
        )
        if memories:
            prefs = "\n".join([m.get("content", {}).get("text", "") for m in memories if m.get("content", {}).get("text")])
            if prefs:
                logger.info(f"Retrieved preferences: {prefs}")
                return f"\n\nUser preferences (remembered from past conversations):\n<preferences>\n{prefs}\n</preferences>\nConsider these preferences in your responses."
    except Exception as e:
        logger.error(f"Preference retrieval error: {e}")

    return ""


def store_interaction(user_id: str, thread_id: str, query: str, response_text: str):
    """Store interaction in memory"""
    if not memory_client or not MEMORY_ID:
        return
    
    if not response_text or not response_text.strip():
        logger.warning("Skipping memory storage: response_text is empty")
        return
    
    try:
        logger.info(f"Storing interaction for user ID: {user_id}, thread ID: {thread_id}")
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=user_id,
            session_id=thread_id,
            messages=[(query, "user"), (response_text, "assistant")]
        )
    except Exception as e:
        logger.error(f"Memory storage error: {e}")
