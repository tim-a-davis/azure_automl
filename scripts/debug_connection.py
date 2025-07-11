#!/usr/bin/env python3
"""Debug script to check database connection"""

import sys
from pathlib import Path

# Force load .env file
from dotenv import load_dotenv

load_dotenv(override=True)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automlapi.config import settings


def main():
    print("=== Azure AutoML Database Connection Debug ===")
    print(f"Environment: {settings.environment}")
    print(f"SQL Server: {settings.sql_server}")
    print(f"SQL Database: {settings.sql_database}")
    print(f"Azure Tenant ID: {settings.azure_tenant_id}")
    print(f"Azure Client ID: {settings.azure_client_id}")
    print(
        f"Azure Client Secret: {'*' * 10 if settings.azure_client_secret else 'NOT SET'}"
    )

    print("\n=== Connection String ===")
    db_url = settings.database_url
    print(f"Database URL: {db_url}")

    print("\n=== Testing Connection ===")
    try:
        from sqlalchemy import text

        from automlapi.db import db_manager

        engine = db_manager.get_engine()
        print("Engine created successfully")

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            print(f"Connection test result: {result.fetchone()}")
            print("✅ Connection successful!")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
