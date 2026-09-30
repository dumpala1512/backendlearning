from fastapi import APIRouter
from app.routers import auth, films, reviews, serialization, users

api_v1_router = APIRouter()

# Register modular routers under /api/v1
api_v1_router.include_router(films.router)
api_v1_router.include_router(reviews.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(serialization.router)
