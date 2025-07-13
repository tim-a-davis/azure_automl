#!/usr/bin/env python3
"""
Script to generate JWT tokens for testing the AutoML API with different roles.

This script creates JWT tokens that include user ID for testing the role-based access control system.
"""

import argparse
import sys
from datetime import datetime, timedelta

import jwt

# Add the src directory to Python path
sys.path.insert(0, "src")

from automlapi.config import settings


def generate_token(user_id: str, expires_hours: int = 24):
    """Generate a JWT token for the given user."""
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token


def main():
    parser = argparse.ArgumentParser(
        description="Generate JWT tokens for AutoML API testing"
    )
    parser.add_argument("user_id", help="User ID for the token")
    parser.add_argument(
        "--expires",
        type=int,
        default=24,
        help="Token expiration in hours (default: 24)",
    )
    parser.add_argument(
        "--show-payload", action="store_true", help="Show token payload"
    )

    args = parser.parse_args()

    token = generate_token(args.user_id, args.expires)

    print(f"Generated JWT token for user '{args.user_id}':")
    print(f"Token: {token}")

    if args.show_payload:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            print(f"Payload: {payload}")
        except Exception as e:
            print(f"Error decoding token: {e}")

    print("\nYou can test this token with curl:")
    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/users')


if __name__ == "__main__":
    main()
    main()
