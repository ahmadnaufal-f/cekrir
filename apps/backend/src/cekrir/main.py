from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import ConnectionPool

from cekrir.api.camera import router as camera_router
from cekrir.api.routes import router
from cekrir.config import Settings, get_settings
from cekrir.db import build_pool
from cekrir.services.tracking import TrackingProvider, TrackingUnavailable, build_tracking_provider


def create_app(
    settings: Settings | None = None,
    pool: ConnectionPool | None = None,
    provider: TrackingProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = pool if pool is not None else build_pool(settings.database_url)
        try:
            if pool is None:
                app.state.pool.open(wait=True, timeout=10)
            with app.state.pool.connection() as connection:
                connection.execute("SELECT 1")
            yield
        finally:
            if pool is None:
                app.state.pool.close()

    app = FastAPI(title="Cekrir API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.tracking_provider = provider or build_tracking_provider(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Ingest-Key"],
    )

    @app.exception_handler(TrackingUnavailable)
    async def tracking_unavailable(request: Request, exc: TrackingUnavailable):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "tracking_provider": settings.tracking_provider}

    app.include_router(router)
    app.include_router(camera_router)
    return app


app = create_app()
