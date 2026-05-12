from functools import wraps
from pathlib import Path
from typing import Optional

import casbin
from fastapi import Header, HTTPException


MOCK_USERS = {
    "token-alice": {"username": "alice", "role": "admin"},
    "token-bob": {"username": "bob", "role": "ml_engineer"},
    "token-carol": {"username": "carol", "role": "data_analyst"},
    "token-dave": {"username": "dave", "role": "intern"},
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
enforcer = casbin.Enforcer(
    str(PROJECT_ROOT / "src" / "access" / "model.conf"),
    str(PROJECT_ROOT / "src" / "access" / "policy.csv"),
)


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Parse a Bearer token and return the mock user context."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1].strip()
    user = MOCK_USERS.get(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user


def require_permission(resource: str, action: str):
    """Check Casbin RBAC permission for the current FastAPI user."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Missing user context")

            username = current_user["username"]
            role = current_user["role"]
            allowed = enforcer.enforce(username, resource, action)

            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{role}' cannot '{action}' on '{resource}'",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
