"""API routes for authentication and token exchange."""

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

try:
    from jwt.jwks_client import PyJWKClient
except Exception:  # pragma: no cover - optional dependency
    PyJWKClient = None
from datetime import datetime, timedelta, timezone

from ..config import settings

router = APIRouter()
security = HTTPBearer()

JWKS_URL = (
    f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
)
jwks_client = PyJWKClient(JWKS_URL) if PyJWKClient else None


class TokenExchangeRequest(BaseModel):
    azure_token: str


class TokenExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str


def validate_azure_token(token: str) -> dict:
    """Validate an Azure AD token and return the claims."""
    try:
        if jwks_client is None:
            raise RuntimeError("PyJWKClient unavailable")

        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=f"api://{settings.azure_client_id}",
            issuer=f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0",
        )

        if "access_as_user" not in claims.get("scp", "").split():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing required scope",
            )

        return claims
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Azure token validation failed: {str(e)}",
        )


@router.post(
    "/auth/exchange",
    response_model=TokenExchangeResponse,
    operation_id="exchange_azure_token",
)
async def exchange_azure_token(request: TokenExchangeRequest) -> TokenExchangeResponse:
    """Exchange an Azure AD token for an API access token.

    Validates the Azure AD token and issues a custom JWT token that can be used
    with the API endpoints.
    """
    # Validate the Azure AD token
    claims = validate_azure_token(request.azure_token)

    # Extract user information from Azure AD token
    user_id = claims.get("oid") or claims.get("sub")  # Object ID or subject
    tenant_id = claims.get("tid")  # Tenant ID
    upn = claims.get("upn")  # User Principal Name
    name = claims.get("name")  # Display name

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Azure token missing required user or tenant information",
        )

    # Create our custom JWT token
    now = datetime.now(timezone.utc)
    expires_in = 3600  # 1 hour
    payload = {
        "sub": user_id,
        "tid": tenant_id,
        "upn": upn,
        "name": name,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": "automl-api",  # Our API as issuer
    }

    try:
        access_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create access token: {str(e)}",
        )

    return TokenExchangeResponse(
        access_token=access_token,
        expires_in=expires_in,
        user_id=user_id,
        tenant_id=tenant_id,
    )


@router.get(
    "/auth/me",
    operation_id="get_current_user_info",
    tags=["mcp"],
)
async def get_current_user_info(
    token: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get information about the currently authenticated user."""
    try:
        payload = jwt.decode(
            token.credentials, settings.jwt_secret, algorithms=["HS256"]
        )
        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tid"),
            "upn": payload.get("upn"),
            "name": payload.get("name"),
            "expires_at": payload.get("exp"),
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
