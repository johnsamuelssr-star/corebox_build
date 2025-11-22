from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/ping")
async def auth_ping():
    return {"status": "ok"}


@router.get("/users")
async def list_users():
    return []
