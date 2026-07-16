from fastapi import APIRouter

from app.api.routes import admin, auth, discussions, folders, providers, proxy


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(discussions.router, prefix="/discussions", tags=["discussions"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
