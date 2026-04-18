from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.responses import JSONResponse
import logging
import time
import uuid
from app.api.endpoints import uploads, files
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.minio import get_minio_client
from app.core.logging import configure_logging, request_id_var
from app.core.telemetry import observe_request, render_metrics

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    context_token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception as error:
            logger.error("HTTP_EXCEPTION", extra={"error_type": type(error).__name__})
            response = JSONResponse(
                {"detail": "Internal server error"}, status_code=500
            )
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = request.scope.get("route")
        path = getattr(route, "path", "/unmatched")
        if response.status_code >= 500:
            logger.error(
                "HTTP_ERROR_RESPONSE",
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                },
            )
        logger.info(
            "HTTP_REQUEST",
            extra={
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        observe_request(duration_ms / 1000)
        return response
    finally:
        request_id_var.reset(context_token)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return render_metrics()


app.include_router(
    uploads.router, prefix=f"{settings.API_V1_STR}/uploads", tags=["uploads"]
)
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(files.router, prefix="/api/files", tags=["files"])


@app.get("/health")
def health_check(db=Depends(get_db)):
    status = {"status": "healthy", "postgres": "down", "redis": "down", "minio": "down"}

    try:
        db.execute(text("SELECT 1"))
        status["postgres"] = "up"
    except Exception:
        status["status"] = "unhealthy"

    try:
        redis_client = get_redis_client()
        if redis_client.ping():
            status["redis"] = "up"
    except Exception:
        status["status"] = "unhealthy"

    try:
        minio_client = get_minio_client()
        # Just check if we can list buckets or catch the exception
        minio_client.list_buckets()
        status["minio"] = "up"
    except Exception:
        status["status"] = "unhealthy"

    return status
