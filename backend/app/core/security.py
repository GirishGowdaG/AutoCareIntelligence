"""Authentication & Role-Based Access Control (RBAC) Engine.

Enforces:
- API key verification via X-API-Key header.
- Limited api_key query-parameter support strictly for browser EventSource on SSE endpoints.
- Role-based authorization across Admin, DealerServiceManager, and FleetAnalyst.
- HTTP 401 for unauthenticated requests and HTTP 403 for forbidden requests.
"""

from enum import Enum
import logging
from typing import Optional, List, Callable

from fastapi import Request, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from backend.app.core.config import get_auth_config

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    """Defined RBAC User Roles."""
    ADMIN = "Admin"
    DEALER_SERVICE_MANAGER = "DealerServiceManager"
    FLEET_ANALYST = "FleetAnalyst"


def authenticate_api_key(
    request: Request,
    api_key_header: Optional[str] = Security(API_KEY_HEADER),
) -> UserRole:
    """Authenticate API key from header or (for SSE exclusively) query parameter.
    
    Returns:
        UserRole if valid key provided.
        
    Raises:
        HTTPException(401): Missing or invalid API key.
    """
    auth_config = get_auth_config()
    provided_key: Optional[str] = api_key_header

    # Browser EventSource query-param fallback strictly for the SSE endpoint
    if not provided_key:
        if request.url.path.rstrip("/").endswith("/api/v1/stream/events"):
            provided_key = request.query_params.get("api_key")

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate against known role credentials
    if provided_key == auth_config.admin_key:
        return UserRole.ADMIN
    elif provided_key == auth_config.dealer_key:
        return UserRole.DEALER_SERVICE_MANAGER
    elif provided_key == auth_config.analyst_key:
        return UserRole.FLEET_ANALYST
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Dependency generator enforcing that authenticated user role is within allowed roles."""
    def rbac_dependency(
        role: UserRole = Security(authenticate_api_key)
    ) -> UserRole:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{role.value}'",
            )
        return role

    return rbac_dependency
