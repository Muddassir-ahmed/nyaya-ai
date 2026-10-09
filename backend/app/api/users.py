from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.dependencies import require_role
from app.models.user import User


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("/admin-test")
async def admin_test(
    current_user: User = Depends(
        require_role("admin")
    ),
):
    return {
        "message": "Admin access granted.",
        "user": current_user.email,
    }


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }