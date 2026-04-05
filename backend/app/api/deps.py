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
from app.core.logging import get_logger
from app.core.supabase import get_admin_client

logger = get_logger(__name__)
settings = get_settings()

_bearer = HTTPBearer(auto_error=True)


class AuthenticatedUser:
    """Carries the decoded JWT payload + resolved profile row."""

    def __init__(self, user_id: str, role: str, phone: str):
        self.user_id = user_id
        self.role = role
        self.phone = phone


class AuthenticatedSession:
    """Carries the decoded JWT payload for any authenticated Supabase session."""

    def __init__(self, user_id: str):
        self.user_id = user_id


def _decode_user_id(credentials: HTTPAuthorizationCredentials) -> str:
    """Validate the bearer token and return the authenticated user id."""
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
        return user_id
    except JWTError as exc:
        logger.warning("JWT validation failed", error=str(exc))
        raise credentials_exception


async def get_authenticated_session(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthenticatedSession:
    """
    Validates the Supabase-issued JWT from the Authorization header.
    Returns the authenticated user id even before a profile exists.
    """
    return AuthenticatedSession(user_id=_decode_user_id(credentials))


async def get_current_user(
    session: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
) -> AuthenticatedUser:
    """
    Resolves a full profile-backed AuthenticatedUser for routes that require one.

    Raises 401 on missing/invalid token or missing profile, 403 if suspended.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Fetch the profile to get role and suspension status
    client = get_admin_client()
    try:
        result = (
            client.table("profiles")
            .select("id, role, phone, is_suspended")
            .eq("id", session.user_id)
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
    except HTTPException:
        raise
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
CurrentSession = Annotated[AuthenticatedSession, Depends(get_authenticated_session)]
CurrentUser    = Annotated[AuthenticatedUser, Depends(get_current_user)]
AdminUser      = Annotated[AuthenticatedUser, Depends(require_role("admin"))]
FundiUser      = Annotated[AuthenticatedUser, Depends(require_role("fundi", "admin"))]
ClientUser     = Annotated[AuthenticatedUser, Depends(require_role("client", "admin"))]
