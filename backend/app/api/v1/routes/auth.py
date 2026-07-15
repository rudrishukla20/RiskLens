from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import LIMIT_LOGIN, LIMIT_REFRESH, limiter
from app.enums.role import RoleEnum
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse, UserMeResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=ResponseEnvelope[TokenResponse])
@limiter.limit(LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates credentials, creating access and refresh tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(
        email=body.email, password=body.password, ip_address=ip_address, user_agent=user_agent
    )
    access_token, refresh_token, expires_in = await auth_service.create_session(
        user=user, ip_address=ip_address, user_agent=user_agent
    )
    await db.commit()
    return build_success_response(
        data=TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=expires_in
        ),
        message="Login successful.",
    )


@router.post("/refresh", response_model=ResponseEnvelope[TokenResponse])
@limiter.limit(LIMIT_REFRESH)
async def refresh(request: Request, body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Rotates refresh token and generates fresh access/refresh tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    auth_service = AuthService(db)
    access_token, refresh_token, expires_in = await auth_service.refresh_session(
        refresh_token=body.refresh_token, ip_address=ip_address, user_agent=user_agent
    )
    await db.commit()
    return build_success_response(
        data=TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=expires_in
        ),
        message="Token refreshed successfully.",
    )


@router.post("/logout", response_model=ResponseEnvelope[None])
async def logout(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invalidates the active refresh token session."""
    auth_service = AuthService(db)
    await auth_service.logout(refresh_token=body.refresh_token, user_id=current_user.id)
    await db.commit()
    return build_success_response(data=None, message="Logout successful.")


@router.get("/me", response_model=ResponseEnvelope[UserMeResponse])
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    """Retrieves profile info for currently logged in user."""
    return build_success_response(
        data=UserMeResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role_code=RoleEnum(current_user.role.code),
        ),
        message="Profile retrieved successfully.",
    )
