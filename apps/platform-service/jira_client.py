import os
import logging

logger = logging.getLogger(__name__)
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

def create_jira_ticket(summary: str, description: str):
    if not JIRA_TOKEN:
        logger.debug(f"[MOCK JIRA] Created ticket: {summary} | Desc: {description}")
        return "MOCK-123"
    
    logger.info(f"[JIRA] Attempting to create real ticket: {summary}")
    return "PROD-456"
