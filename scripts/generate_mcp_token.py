#!/usr/bin/env python3
"""Quick script to generate a JWT token for MCP authentication."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from scripts.create_token import create_token


def main():
    """Generate a JWT token and provide instructions for MCP setup."""
    print("=== AutoML MCP Authentication Setup ===\n")

    # Create a token for testing (24 hour expiry)
    user_id = "mcp-user"
    tenant_id = "test-tenant"

    try:
        token = create_token(user_id, tenant_id, hours=24)

        print("Generated JWT token for MCP authentication:")
        print(f"User ID: {user_id}")
        print(f"Tenant ID: {tenant_id}")
        print("Expires: 24 hours from now")
        print()
        print("Token:")
        print(token)
        print()

        print("=== Setup Instructions ===")
        print("1. Start your AutoML API server:")
        print("   cd /Users/tdavis4_1/Desktop/projects/azure_automl")
        print("   python -m src.automlapi.runserver")
        print()
        print(
            "2. In VS Code, when prompted for 'JWT Token for AutoML API Authentication',"
        )
        print("   paste the token shown above.")
        print()
        print("3. The MCP server should now authenticate successfully!")
        print()
        print(
            "Note: The token expires in 24 hours. Run this script again to generate a new one."
        )

    except Exception as e:
        print(f"Error generating token: {e}")
        print("Make sure JWT_SECRET is set in your .env file")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
