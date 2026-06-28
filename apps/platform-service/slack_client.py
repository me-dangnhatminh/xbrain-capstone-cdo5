import requests
import os
import logging

logger = logging.getLogger(__name__)
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

def send_slack_message(message: str):
    if not SLACK_WEBHOOK:
        # Sử dụng DEBUG log cho Mock thay vì print
        logger.debug(f"[MOCK SLACK] {message}")
        return
        
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload)
        response.raise_for_status()
        logger.info("[SLACK] Message sent successfully!")
    except Exception as e:
        logger.error(f"[SLACK ERROR] Failed to send message: {e}")
