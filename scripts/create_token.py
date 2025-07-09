#!/usr/bin/env python
"""Generate a JWT token for testing the Azure AutoML API."""

# Load JWT secret from environment
import os
import sys
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    print("Error: JWT_SECRET not found in environment variables or .env file")
    sys.exit(1)


def create_token(user_id: str, tenant_id: str = "test-tenant", hours: int = 24):
    """Create a JWT token for the given user and tenant."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,  # Subject (user identifier)
        "tid": tenant_id,  # Tenant ID
        "iat": now,  # Issued at
        "exp": now + timedelta(hours=hours),  # Expiration
    }

    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return token
    except Exception as e:
        print(f"Error creating JWT token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_token.py <user_id> [tenant_id] [hours]")
        print("Example: python create_token.py user123 my-tenant 24")
        sys.exit(1)

    user_id = sys.argv[1]
    tenant_id = sys.argv[2] if len(sys.argv) > 2 else "test-tenant"
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24

    token = create_token(user_id, tenant_id, hours)
    print(
        f"JWT Token for user '{user_id}' (tenant: '{tenant_id}', expires in {hours} hours):"
    )
    print(token)
    print("\nUse this token in your requests:")
    print(f"Authorization: Bearer {token}")
    print(f"Authorization: Bearer {token}")
