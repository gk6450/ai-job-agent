"""Simple bearer token authentication for single-user setup."""

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import WEB_AUTH_TOKEN

security = HTTPBearer(auto_error=False)


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the bearer token. Skip auth in dev mode if no token is set."""
    if WEB_AUTH_TOKEN == "jobpilot-local-dev":
        return True

    if not credentials or credentials.credentials != WEB_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")
    return True
