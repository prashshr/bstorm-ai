from fastapi import APIRouter

from app.api.routes import auth, discussions, providers, proxy


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(discussions.router, prefix="/discussions", tags=["discussions"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
