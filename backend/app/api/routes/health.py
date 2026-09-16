from fastapi import APIRouter
from sqlalchemy import text
import redis

from app.core.config import settings
from app.core.database import engine


router = APIRouter()


@router.get("/health")
def health_check():
    """
    Liveness probe.

    Confirms that the Evidentia API process is running.
    This endpoint deliberately avoids dependency checks.
    """

    return {
        "status": "healthy",
        "service": "Evidentia API",
        "version": "0.1.0",
    }


@router.get("/ready")
def readiness_check():
    """
    Readiness probe.

    Verifies that the infrastructure required by
    Evidentia is reachable before reporting the service
    as ready.
    """

    checks = {
        "postgres": False,
        "redis": False,
    }

    # -----------------------------------------------------
    # PostgreSQL
    # -----------------------------------------------------

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        checks["postgres"] = True

    except Exception as exc:
        print(
            "PostgreSQL readiness check failed: "
            f"{exc}"
        )

    # -----------------------------------------------------
    # Redis
    # -----------------------------------------------------

    try:
        redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

        redis_client.ping()

        checks["redis"] = True

    except redis.RedisError as exc:
        print(
            "Redis readiness check failed: "
            f"{exc}"
        )

    ready = all(
        checks.values()
    )

    return {
        "status": (
            "ready"
            if ready
            else "degraded"
        ),
        "service": "Evidentia API",
        "version": "0.1.0",
        "checks": checks,
    }