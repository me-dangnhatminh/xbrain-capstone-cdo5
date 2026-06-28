import asyncio
import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from config import config
from dependencies import get_incident_service
from routers.incident_router import router as incident_router
from routers.health_router import router as health_router
from services.sqs_consumer import SQSConsumer

# --- Logging setup (SRP: tập trung tại đây, không rải rác) ---
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


from models.incident import TriageRequest

# --- SQS alert handler (bridge SQS message → IncidentService) ---
async def handle_alert(body: dict) -> None:
    """
    Adapter chuyển dict từ SQS thành TriageRequest và gọi service.
    """
    request = TriageRequest(**body)
    service = get_incident_service()
    await service.handle(request)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Lifespan context manager thay thế on_event("startup") deprecated.
    SRP: main.py chịu trách nhiệm khởi động background task.
    SQSConsumer được inject handler từ bên ngoài (DIP).
    """
    consumer = SQSConsumer(message_handler=handle_alert)
    task = asyncio.create_task(consumer.poll())
    logger.info("SQS consumer started.")
    yield
    task.cancel()


# --- App bootstrap ---
app = FastAPI(title=config.APP_NAME, lifespan=lifespan)
app.include_router(incident_router)
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)