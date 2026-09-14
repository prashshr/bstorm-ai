from fastapi import APIRouter

from app.api.routes import admin, auth, discussions, folders, personas, providers, providers_oauth, proxy, user


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(providers_oauth.router, prefix="/providers/oauth", tags=["providers-oauth"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(discussions.router, prefix="/discussions", tags=["discussions"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
