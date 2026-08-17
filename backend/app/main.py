from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from sqlalchemy import text
from app.core.database import Base, engine
from app.modules import ai, auth, master_data, operations, telemetry

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            connection.execute(text("SELECT create_hypertable('telemetry_details', 'measurement_timestamp', if_not_exists => TRUE, migrate_data => TRUE)"))
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for module in (auth, master_data, telemetry, operations, ai):
    app.include_router(module.router, prefix=settings.api_prefix)
Instrumentator().instrument(app).expose(app)

@app.get("/health", tags=["Platform"])
def health():
    return {"status": "healthy", "service": "backend", "environment": settings.app_env}
