from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from cekrir.api.routes import router
from cekrir.config import Settings, get_settings
from cekrir.db import build_engine
from cekrir.services.tracking import TrackingProvider, TrackingUnavailable, build_tracking_provider


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    provider: TrackingProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine if engine is not None else build_engine(settings.database_url)
        SQLModel.metadata.create_all(app.state.engine)
        yield
        if engine is None:
            app.state.engine.dispose()

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
    return app


app = create_app()
