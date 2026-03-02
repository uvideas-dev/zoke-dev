import os
from fastapi import FastAPI
from app.core.config import settings
from app.core import security  # Force Firebase initialization
from app.db.session import engine, Base, check_db_connection
from app.core.redis_client import get_redis, check_redis_connection
from app.api.v1.endpoints import api_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.joke_ingestion import fetch_and_store_jokes

app = FastAPI(title="ZoKe API", version="0.1.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    print("🚀 App starting up...")
    
    # 1. DB connection check
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_ok = await check_db_connection()
    if db_ok:
        print("✅ Database: Connected")
    else:
        print("❌ Database: Connection FAILED")

    # 2. Redis connection check (Mock fallback is built-in)
    redis_ok = await check_redis_connection()
    if redis_ok:
        print("✅ Redis: Connected")
    else:
        print("⚠️ Redis: Using in-memory fallback")
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_store_jokes, "cron", hour=0, minute=0)
    scheduler.start()

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    db_status = await check_db_connection()
    redis_status = await check_redis_connection()
    
    return {
        "status": "ok" if db_status else "degraded",
        "environment": "production" if os.getenv("RENDER") else "development",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "fallback"
    }

@app.get("/")
async def root():
    return {"message": "Welcome to ZoKe API - Ready for Humor!"}

# Logging configuration
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"UNHANDLED ERROR: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal ZoKe Error. Please check backend logs."}
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response

app.include_router(api_router, prefix="/api/v1")
