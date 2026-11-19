from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cekrir.config import Settings, get_settings
from cekrir.db.redis import RedisConnections
from cekrir.db.session import build_engine, build_session_factory
from cekrir.middleware import RolePermissionMiddleware
from cekrir.routers import (
    auth_router,
    camera_router,
    detection_router,
    notification_router,
    shipment_router,
)
from cekrir.routers.payments import router as payment_router
from cekrir.services.auth import ensure_bootstrap_admin
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider, TrackingUnavailable, build_tracking_provider


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    provider: TrackingProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    owns_engine = engine is None
    engine = engine or build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    redis = RedisConnections(settings.redis_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            redis.check()
            ensure_bootstrap_admin(session_factory, settings)
            yield
        finally:
            await redis.close()
            if owns_engine:
                engine.dispose()

    app = FastAPI(title="Cekrir API", version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis = redis
    app.state.notification_publisher = NotificationPublisher(redis.client)
    app.state.tracking_provider = provider or build_tracking_provider(settings)

    app.add_middleware(RolePermissionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Ingest-Key", "Idempotency-Key"],
    )

    @app.exception_handler(TrackingUnavailable)
    async def tracking_unavailable(request: Request, exc: TrackingUnavailable):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health", tags=["health"])
    def health():
        return {
            "status": "ok",
            "tracking_provider": settings.tracking_provider,
            "redis": "ok" if redis.available else "unavailable",
        }

    app.include_router(auth_router)
    app.include_router(shipment_router)
    app.include_router(detection_router)
    app.include_router(camera_router)
    app.include_router(notification_router)
    app.include_router(payment_router)
    return app


app = create_app()
