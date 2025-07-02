from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

from .config import settings

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        payload = jwt.decode(token.credentials, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=403)
