"""Routes handling RBAC token verification and Azure role assignments."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
try:
    from jwt.jwks_client import PyJWKClient
except Exception:  # pragma: no cover - optional dependency
    PyJWKClient = None
from azure.identity import OnBehalfOfCredential
from azure.mgmt.authorization import AuthorizationManagementClient

from ..config import settings

router = APIRouter()
security = HTTPBearer()

JWKS_URL = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
jwks_client = PyJWKClient(JWKS_URL) if PyJWKClient else None


def verify_token(auth: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = auth.credentials
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed")
    if "access_as_user" not in claims.get("scp", "").split():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing required scope")
    return token


@router.get(
    "/rbac/assignments",
    operation_id="list_rbac_assignments",
)
def list_assignments(user_token: str = Depends(verify_token)) -> list[dict]:
    """List Azure role assignments for the caller.

    Uses on-behalf-of flow to query the Management API with the caller's token.
    """
    credential = OnBehalfOfCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        user_assertion=user_token,
    )
    client = AuthorizationManagementClient(credential, settings.azure_subscription_id)
    scope = f"/subscriptions/{settings.azure_subscription_id}"
    assignments = list(client.role_assignments.list_for_scope(scope))
    return [a.as_dict() for a in assignments]
