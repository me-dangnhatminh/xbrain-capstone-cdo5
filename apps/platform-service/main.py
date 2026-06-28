import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from slack_client import send_slack_message
from jira_client import create_jira_ticket
import uvicorn

# Cấu hình Logging 12-Factor
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ENV_NAME = os.getenv("ENV_NAME", "local")

app = FastAPI(title="CDO Platform Service")

class IncidentReport(BaseModel):
    incident_id: str
    root_cause: str
    confidence: str

@app.on_event("startup")
def startup_event():
    logger.info(f"Platform Service started in [{ENV_NAME}] environment. Log level: {LOG_LEVEL}")

@app.post("/api/v1/notify")
def notify_incident(report: IncidentReport):
    logger.info(f"Received incident report for {report.incident_id}")
    
    # 1. Gọi hàm tạo Jira ticket
    ticket_id = create_jira_ticket(
        summary=f"Incident {report.incident_id}",
        description=f"Root cause: {report.root_cause} (Confidence: {report.confidence})"
    )
    
    # 2. Lắp ráp tin nhắn và gửi Slack
    slack_msg = f"🚨 *New Incident:* {report.incident_id}\n*Environment:* {ENV_NAME}\n*Jira:* {ticket_id}\n*Root Cause:* {report.root_cause} ({report.confidence})"
    send_slack_message(slack_msg)
    
    return {"status": "success", "ticket_id": ticket_id, "environment": ENV_NAME}

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": ENV_NAME}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
