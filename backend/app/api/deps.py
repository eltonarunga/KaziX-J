"""
app/api/deps.py
───────────────
FastAPI dependency functions.
Import these with Depends() in route handlers.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.supabase import get_admin_client
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_bearer = HTTPBearer(auto_error=True)


class AuthenticatedUser:
    """Carries the decoded JWT payload + resolved profile row."""

    def __init__(self, user_id: str, role: str, phone: str):
        self.user_id = user_id
        self.role = role
        self.phone = phone


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthenticatedUser:
    """
    Validates the Supabase-issued JWT from the Authorization header.
    Returns a lightweight AuthenticatedUser object.

    Raises 401 on missing/invalid token, 403 if account is suspended.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Note: Supabase uses HS256 with the JWT_SECRET for signing
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError as exc:
        logger.warning("JWT validation failed", error=str(exc))
        raise credentials_exception

    # Fetch the profile to get role and suspension status
    client = get_admin_client()
    try:
        result = (
            client.table("profiles")
            .select("id, role, phone, is_suspended")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            raise credentials_exception

        profile = result.data
        if profile.get("is_suspended"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended. Contact support.",
            )

        return AuthenticatedUser(
            user_id=profile["id"],
            role=profile["role"],
            phone=profile["phone"],
        )
    except Exception as e:
        logger.error("Database error in get_current_user", error=str(e))
        raise credentials_exception


def require_role(*roles: str):
    """
    Factory: returns a dependency that enforces one of the given roles.

    Usage:
        @router.get("/admin/users")
        async def list_users(
            _: Annotated[AuthenticatedUser, Depends(require_role("admin"))]
        ): ...
    """

    async def _check(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}",
            )
        return user

    return _check


# Convenience aliases
CurrentUser  = Annotated[AuthenticatedUser, Depends(get_current_user)]
AdminUser    = Annotated[AuthenticatedUser, Depends(require_role("admin"))]
FundiUser    = Annotated[AuthenticatedUser, Depends(require_role("fundi", "admin"))]
ClientUser   = Annotated[AuthenticatedUser, Depends(require_role("client", "admin"))]
