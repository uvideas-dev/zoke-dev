from fastapi import APIRouter
from app.api.v1.endpoints import jokes, rezokes, users, social

api_router = APIRouter()
api_router.include_router(jokes.router, prefix="/jokes", tags=["jokes"])
api_router.include_router(rezokes.router, prefix="/rezokes", tags=["rezokes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
