from fastapi import APIRouter
from app.api.routes.pages import router as pages_router

router = APIRouter()
router.include_router(pages_router)
