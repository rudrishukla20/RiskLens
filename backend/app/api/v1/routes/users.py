import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[UserListResponse])
async def list_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Lists accounts of all registered users (Admin-only)."""
    service = UserService(db, admin_user)
    items = await service.list_users(skip=skip, limit=limit)

    # Query total users count
    total_stmt = select(func.count(User.id))
    total = (await db.execute(total_stmt)).scalar() or 0

    # Map to schema
    user_responses = [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            status=u.status,
            role_code=u.role.code,  # Will serialize to "role" in the response alias
            last_login_at=u.last_login_at,
            created_by=u.created_by,
            deactivated_at=u.deactivated_at,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in items
    ]

    return build_success_response(
        data=UserListResponse(items=user_responses, total=total), message="Users list retrieved successfully."
    )


@router.post("", response_model=ResponseEnvelope[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    """Creates/provisions a new user account (Admin-only)."""
    service = UserService(db, admin_user)
    u = await service.create_user(
        email=body.email, full_name=body.full_name, password=body.password, role_code=body.role_code
    )
    data = UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        status=u.status,
        role_code=u.role.code,
        last_login_at=u.last_login_at,
        created_by=u.created_by,
        deactivated_at=u.deactivated_at,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )
    await db.commit()

    return build_success_response(
        data=data,
        message="User account created successfully.",
    )


@router.get("/{user_id}", response_model=ResponseEnvelope[UserResponse])
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    """Retrieves detailed profile metadata for a specific user (Admin-only)."""
    service = UserService(db, admin_user)
    u = await service.get_user(user_id)
    return build_success_response(
        data=UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            status=u.status,
            role_code=u.role.code,
            last_login_at=u.last_login_at,
            created_by=u.created_by,
            deactivated_at=u.deactivated_at,
            created_at=u.created_at,
            updated_at=u.updated_at,
        ),
        message="User details retrieved successfully.",
    )


@router.patch("/{user_id}", response_model=ResponseEnvelope[UserResponse])
async def update_user(
    user_id: uuid.UUID, body: UserUpdate, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Updates selected settings profile properties for a user (Admin-only)."""
    service = UserService(db, admin_user)
    u = await service.update_user(
        user_id=user_id,
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        role_code=body.role_code,
        status=body.status,
    )
    data = UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        status=u.status,
        role_code=u.role.code,
        last_login_at=u.last_login_at,
        created_by=u.created_by,
        deactivated_at=u.deactivated_at,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )
    await db.commit()
    return build_success_response(
        data=data,
        message="User profile updated successfully.",
    )


@router.patch("/{user_id}/deactivate", response_model=ResponseEnvelope[UserResponse])
async def deactivate_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Deactivates a user account (soft delete, Admin-only)."""
    service = UserService(db, admin_user)
    u = await service.deactivate_user(user_id)
    data = UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        status=u.status,
        role_code=u.role.code,
        last_login_at=u.last_login_at,
        created_by=u.created_by,
        deactivated_at=u.deactivated_at,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )
    await db.commit()
    return build_success_response(
        data=data,
        message="User deactivated successfully.",
    )
